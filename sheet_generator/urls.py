from django.conf.urls import url

from .views import download_sheet, download_sheet_api
from django.views.generic import TemplateView

urlpatterns = [
    url(
        r'^$',
        TemplateView.as_view(template_name='sheet_generator/index.html'),
        name='index_sheet_generator'
    ),
    url(r'^download/$', download_sheet, name='download_sheet_url'),
    url(r'^download/api/$', download_sheet_api, name='download_sheet_api_url'),
]
