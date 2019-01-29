import os
from sheet_generator.apps import APP_DIR

from django_sopila.settings import ABJAD_TONES, BEAT
from abjad import Staff
from abjad.system.PersistenceManager import PersistenceManager

class ToneParser:

    tone_list = []

    def __init__(self):
        with open(os.path.join(APP_DIR, 'test_data.txt'), 'r') as file:
            self.tone_list = file.read().split(' ')
            self.tone_list = [int(i) for i in self.tone_list]

        if not self.tone_list:
            raise ValueError('Data from file "%s" cannot be processed.' % (filename))

    def strip_silence(self):
        '''
        Returns list without first and last n examples of silence class (13).
        '''
        start_idx = 0
        end_idx = -1
        # class position
        silence = 12
        for i, tone in enumerate(self.tone_list):
            if tone != silence:
                start_idx = i
                break

        for i, tone in reversed(list(enumerate(self.tone_list))):
            if tone != silence:
                end_idx = i - 1
                break

        self.tone_list = self.tone_list[start_idx:end_idx]

    def get_abjad_tone(self, tone_class_number):
        return ABJAD_TONES[tone_class_number]

    def get_tones_dict(self):
        '''
        Returnes list of tuples. First value in the tuple is abjad tone name and
        second value is number of consecutive frames with that tone.
        '''
        new_tone_list = []
        tone_length = 0

        prev = self.tone_list[0]
        for i, tone in enumerate(self.tone_list[1:]):
            tone_length += 1
            if prev != tone:
                new_tone_list.append((self.get_abjad_tone(tone), tone_length))
                # reset
                tone_length = 0
                prev = tone

        # append last
        last_dict_name = self.tone_list[-1]
        new_tone_list.append((self.get_abjad_tone(last_dict_name), tone_length))

        return new_tone_list

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

    def parse_tones(self, filename):
        self.strip_silence()
        tones_string = ''
        for tone in self.get_tones_dict():
            duration = self.get_duration_label(tone[1])
            if duration:
                tones_string += tone[0] + duration + ' '
        staff = Staff(tones_string)
        PersistenceManager(client=staff).as_pdf(os.path.join(APP_DIR, 'pdf', filename))
