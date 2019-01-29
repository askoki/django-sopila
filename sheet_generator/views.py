from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect


def download_sheet(request):
    # from io import BytesIO

    # response = HttpResponse(pdf)
    # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % ('sopila_sheet')
    # return response
    return render(
        request,
        'sheet_generator/index.html',
        {
            'success': True
        }
    )


