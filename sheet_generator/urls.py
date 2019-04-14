from django.conf.urls import url

from .views import download_sheet_api, upload_recording_api
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^download/api/(?P<filename>\w+)/$', download_sheet_api, name='download_sheet_api_url'),
    url(r'^upload/$', upload_recording_api, name='upload_recording_url')
]
