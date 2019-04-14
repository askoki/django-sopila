import os
from sheet_generator.apps import APP_DIR

from django.core.files.storage import default_storage

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, \
HttpResponseNotAllowed, HttpResponseServerError
from sheet_generator.utils import ToneParser
from .forms import UploadFileForm


def download_sheet(request):

    sheet = ToneParser()
    filename = 'test.pdf'
    sheet.parse_tones(filename)

    pdf = open(os.path.join(APP_DIR, 'pdf', filename), 'rb')
    response = HttpResponse(pdf)
    response[
        'Content-Disposition'
    ] = 'attachment; filename=%s.pdf' % ('sopila_sheet')

    return response


def download_sheet_api(request):

    sheet = ToneParser()
    filename = 'test.pdf'
    sheet.parse_tones(filename)

    pdf = open(os.path.join(APP_DIR, 'pdf', filename), 'rb')
    response = HttpResponse(pdf)
    response[
        'Content-Disposition'
    ] = 'attachment; filename=%s.pdf' % ('sopila_sheet')
    return response


@csrf_exempt
def upload_recording_api(request):

    if request.method != 'POST':
        return HttpResponseNotAllowed('Only POST here')

    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseServerError("Invalid call")

    #  Saving POST'ed file to storage
    file = request.FILES['audio']
    file_name = default_storage.save(file.name, file)
    return HttpResponse('OK')
