import os
import re
import h5py
import numpy as np
from sheet_generator.apps import APP_DIR
from django_sopila.settings import MEDIA_ROOT, BASE_DIR
from pydub import AudioSegment
from joblib import load

from django_sopila.settings import ABJAD_TONES, BEAT
from abjad import Staff, Voice, LilyPondLiteral, attach, Container
from abjad.system.PersistenceManager import PersistenceManager


def level_combined_recording(audio_file):
    # skip non stereo (uncombined) files
    if audio_file.channels <= 1:
        # skip whole folder
        return audio_file

    left, right = audio_file.split_to_mono()
    diff = abs(left.dBFS - right.dBFS)

    # compare left and right channel in dBFS
    get_gain = lambda l_ch, r_ch: 0 if l_ch > r_ch else diff

    left = left.apply_gain(get_gain(left.dBFS, right.dBFS))
    right = right.apply_gain(get_gain(right.dBFS, left.dBFS))

    audio_file = left.overlay(right)
    return audio_file


def normalize_amplitudes(amplitudes):
    # 50 db is like quiet restaurant
    # 10 * log10(x) = 50
    CUTOFF_THRESHOLD = 100000

    if amplitudes[amplitudes >= CUTOFF_THRESHOLD].any():
        amplitudes = abs(amplitudes) ** 2
        max_amplitude = amplitudes.max() if amplitudes.max() != 0 else 1.0
    else:
        # max threshold approx 20% of max value
        max_percentage = 0.2
        amplitudes = abs(amplitudes) * max_percentage
        max_amplitude = CUTOFF_THRESHOLD

    return amplitudes / max_amplitude


def make_prediction_file(filename):

    start = 0
    # in miliseconds
    step = 10
    audio_file = AudioSegment.from_wav(
        os.path.join(MEDIA_ROOT, filename + '.wav')
    )

    # measured in miliseconds
    duration = len(audio_file)
    number_of_segments = int(duration / step)

    all_norm_amplitudes = []
    for i in range(0, number_of_segments):
        end = start + step
        audio_segment = audio_file[start:end]

        # one cut segment
        # level segment if needed
        audio_segment = level_combined_recording(audio_segment)
        fft = np.fft.fft(np.array(audio_segment.get_array_of_samples()))

        N = fft.size
        f = abs(np.fft.fftfreq(N) * audio_segment.frame_rate)
        norm_amplitudes = normalize_amplitudes(fft)

        all_norm_amplitudes.append(norm_amplitudes)

        # end of cut segment
        start += step

    rnd_clf = load(os.path.join(BASE_DIR, 'rf_polyphonic_model.joblib'))
    y_predicted = rnd_clf.predict(all_norm_amplitudes)

    predicted_file = h5py.File(
        os.path.join(
            APP_DIR, 'raw_predictions', filename + '.hdf5'
        ),
        'w'
    )
    dt = h5py.special_dtype(vlen=str)
    predicted_file.create_dataset(
        'predictions',
        data=y_predicted,
        dtype=dt
    )
    predicted_file.close()


class ToneParser:

    tone_list = []

    def __init__(self, filename):
        predicted_file = h5py.File(
            os.path.join(
                APP_DIR, 'raw_predictions', filename + '.hdf5'
            ),
            'r'
        )
        self.filename = filename
        self.tone_list = predicted_file['predictions'].value.tolist()
        predicted_file.close()

        if not self.tone_list:
            raise ValueError(
                'Data from file "%s" cannot be processed.' % (filename))

    def strip_silence(self):
        """
        Returns list without first and last n examples of silence class (13).
        """
        start_idx = 0
        end_idx = -1
        # class position
        for i, tone in enumerate(self.tone_list):
            if not 'silence' in tone:
                start_idx = i
                break

        for i, tone in reversed(list(enumerate(self.tone_list))):
            if not 'silence' in tone:
                end_idx = i - 1
                break

        self.tone_list = self.tone_list[start_idx:end_idx]

    def get_abjad_tones(self, tone_class_name):
        """
        Returns tuple containing mala and vela values.
        """

        try:
            mala = re.search('m\d', tone_class_name).group(0)
        except AttributeError:
            mala = None

        try:
            vela = re.search('v\d', tone_class_name).group(0)
        except AttributeError:
            vela = None

        # pause
        if not mala:
            mala = 'pause'
        if not vela:
            vela = 'pause'

        return (ABJAD_TONES[mala], ABJAD_TONES[vela])

    def merge_same_tones(self, tone_list):
        """
        tone_list => list of tuples containing information about mala class,
        vela class and duration.
        Returns squashed list with distinct values in sequence array example:
        aaabbbccc becomes abc
        """
        merged_tone_list = {'m': [], 'v': []}

        prev_mala = tone_list[0][0]
        prev_vela = tone_list[0][1]

        # same length on the beggining
        prev_mala_tone_length = tone_list[0][2]
        prev_vela_tone_length = tone_list[0][2]

        for mala_tone, vela_tone, tone_length in tone_list[1:]:

            if prev_mala == mala_tone:
                prev_mala_tone_length += tone_length
            else:
                merged_tone_list['m'].append(
                    (prev_mala, prev_mala_tone_length))
                prev_mala_tone_length = tone_length
                prev_mala = mala_tone

            if prev_vela == vela_tone:
                prev_vela_tone_length += tone_length
            else:
                merged_tone_list['v'].append(
                    (prev_vela, prev_vela_tone_length))
                prev_vela_tone_length = tone_length
                prev_vela = vela_tone

        # append last tone
        if prev_mala_tone_length > 0:
            merged_tone_list['m'].append((prev_mala, prev_mala_tone_length))

        if prev_vela_tone_length > 0:
            merged_tone_list['v'].append((prev_vela, prev_vela_tone_length))

        return merged_tone_list

    def get_tones_dict(self):
        """
        Returnes tuple containing two list of tuples. First list is set of
        tone and duration values of 'mala' and second are values of 'vela'.
        First value in each tuple is abjad tone name and second value is
        number of consecutive frames with that tone.
        """
        tone_list = []
        tone_length = 0
        # if tone is missclassified then tone length is assigned to next tone
        transition_length = 0
        IGNORE_THRESHOLD = 3

        prev = self.tone_list[0]
        for i, tone_class_name in enumerate(self.tone_list[1:]):
            tone_length += 1
            if prev != tone_class_name:
                mala_tone, vela_tone = self.get_abjad_tones(prev)

                if tone_length <= IGNORE_THRESHOLD:
                    transition_length += tone_length
                else:
                    tone_list.append(
                        (mala_tone, vela_tone, tone_length + transition_length)
                    )
                    transition_length = 0
                # reset
                tone_length = 0
                prev = tone_class_name

        # append last
        if tone_length >= IGNORE_THRESHOLD:
            last_dict_name = self.tone_list[-1]
            mala_tone, vela_tone = self.get_abjad_tones(last_dict_name)
            tone_list.append((mala_tone, vela_tone, tone_length))

        # tones are here in abjad format (not in class format)
        return self.merge_same_tones(tone_list)

    def get_duration_label(self, frames):

        if frames > 4 * BEAT:
            return '1'
        elif 2 * BEAT < frames:
            return '2'
        elif BEAT < frames:
            return '4'
        elif BEAT / 2 < frames:
            return '8'
        elif BEAT / 4 < frames:
            return '16'
        elif BEAT / 8 < frames:
            return '32'
        # if beat is smaller then it is discarded
        return None

    def parse_tones(self):
        self.strip_silence()
        notes = Staff()
        # remove measure and tacts
        notes.remove_commands.append('Time_signature_engraver')
        notes.remove_commands.append('Bar_engraver')

        mala_voice = ""
        vela_voice = ""
        tones_dict = self.get_tones_dict()
        for mala_tone, tone_length in tones_dict['m']:
            duration = self.get_duration_label(tone_length)

            if duration:
                mala_voice += mala_tone + duration + " "

        for vela_tone, tone_length in tones_dict['v']:
            duration = self.get_duration_label(tone_length)

            if duration:
                vela_voice += vela_tone + duration + " "

        mala_voice = Voice(mala_voice, name='mala voice')
        literal = LilyPondLiteral(r'\voiceOne')
        attach(literal, mala_voice)

        vela_voice = Voice(vela_voice, name='vela voice')
        literal = LilyPondLiteral(r'\voiceTwo')
        attach(literal, vela_voice)

        container = Container([mala_voice, vela_voice])
        container.is_simultaneous = True
        notes.append(container)

        PersistenceManager(client=notes).as_pdf(
            os.path.join(APP_DIR, 'pdf', self.filename + ".pdf")
        )
