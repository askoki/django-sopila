import os
from sheet_generator.apps import APP_DIR

from django.http import JsonResponse
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from sheet_generator.utils import ToneParser


def download_sheet(request):

    sheet = ToneParser()
    filename = 'test.pdf'
    sheet.parse_tones(filename)

    pdf = open(os.path.join(APP_DIR, 'pdf', filename), 'rb')
    response = HttpResponse(pdf)
    response['Content-Disposition'] = 'attachment; filename=%s.pdf' % ('sopila_sheet')

    return response

def download_sheet_api(request):

    sheet = ToneParser()
    filename = 'test.pdf'
    sheet.parse_tones(filename)

    pdf = open(os.path.join(APP_DIR, 'pdf', filename), 'rb')
    response = HttpResponse(pdf)
    response['Content-Disposition'] = 'attachment; filename=%s.pdf' % ('sopila_sheet')
    return response
