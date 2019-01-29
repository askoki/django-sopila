import os
from sheet_generator.apps import APP_DIR

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

    return render(
        request,
        'sheet_generator/index.html',
        {
            'success': True
        }
    )
