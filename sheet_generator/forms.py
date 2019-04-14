from django import forms


class UploadFileForm(forms.Form):
    audio  = forms.FileField()