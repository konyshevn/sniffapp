from django import forms
import os
from upload_file.models import *
from upload_file.config import *

def file_list():
    files = []
    for file in os.listdir(file_dir):
        if len(file.split('.')[-1]) > 3:
            continue
        files.append((file, file))
    return files


def uid_list():
    uids = [(uid.uid, uid) for uid in Uid.objects.all()]
    return uids


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50, required=False)
    file = forms.FileField()


class SelectFiles(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SelectFiles, self).__init__(*args, **kwargs)
        self.fields['selected_files'] = forms.MultipleChoiceField(widget=forms.widgets.CheckboxSelectMultiple, choices=file_list())


class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['uid'] = forms.CharField(widget=forms.widgets.Select(choices=uid_list()))

    src = forms.GenericIPAddressField(required=False)
    dst = forms.GenericIPAddressField(required=False)
    date_from = forms.DateTimeField(required=False, input_formats=('%Y-%m-%d %H:%M',), widget=forms.DateTimeInput(format=('%Y-%m-%d %H:%M',), attrs={'type': 'datetime-local'}))
    date_until = forms.DateTimeField(required=False, input_formats=('%Y-%m-%d %H:%M',), widget=forms.DateTimeInput(format=('%Y-%m-%d %H:%M',), attrs={'type': 'datetime-local'}))
