from django import forms
import os
from django.conf import settings
from .models import BackupLog, BackupRestoreRequest
from .apps_models_list import APPS_MODELS


class BackupLogAdminForm(forms.ModelForm):
    app_name = forms.ChoiceField(
        choices=[(app, app.capitalize()) for app in APPS_MODELS.keys()],
        label="انتخاب اپلیکیشن",
        required=True
    )
    model_name = forms.ChoiceField(
        choices=[],
        label="انتخاب مدل",
        required=False
    )
    file_path = forms.ChoiceField(
        choices=[],
        label="فایل بکاپ",
        required=True
    )

    class Meta:
        model = BackupLog
        fields = ['backup_type', 'app_name', 'model_name']  # file_path در مدل نیست

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        selected_app = None
        if 'app_name' in self.data:
            selected_app = self.data.get('app_name')
        elif self.instance and self.instance.app_name:
            selected_app = self.instance.app_name

        if selected_app in APPS_MODELS:
            model_choices = [(m, m) for m in APPS_MODELS[selected_app]]
            self.fields['model_name'].choices = model_choices
            self.fields['model_name'].widget.attrs.pop('disabled', None)
        else:
            self.fields['model_name'].choices = []
            self.fields['model_name'].widget.attrs['disabled'] = True

        backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
        file_choices = []
        if os.path.exists(backup_folder) and os.path.isdir(backup_folder):
            file_choices = [
                (f, f)
                for f in os.listdir(backup_folder)
                if os.path.isfile(os.path.join(backup_folder, f))
            ]

        if file_choices:
            self.fields['file_path'].choices = file_choices
            self.fields['file_path'].widget.attrs.pop('disabled', None)
        else:
            self.fields['file_path'].choices = []
            self.fields['file_path'].widget.attrs['disabled'] = True
            self.fields['file_path'].help_text = "پوشه بکاپ پیدا نشد یا فایل موجود نیست."

    def clean_file_path(self):
        file_name = self.cleaned_data.get('file_path')
        backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
        full_path = os.path.join(backup_folder, file_name)
        if not os.path.exists(full_path):
            raise forms.ValidationError("فایل انتخاب شده در پوشه بکاپ وجود ندارد.")
        return file_name

    def save(self, commit=True):
        instance = super().save(commit=False)
        file_name = self.cleaned_data.get('file_path')
        if file_name:
            backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
            full_path = os.path.join(backup_folder, file_name)
            # باز کردن فایل بکاپ و قرار دادن در فیلد backup_file مدل
            with open(full_path, 'rb') as f:
                from django.core.files.base import File
                django_file = File(f)
                instance.backup_file.save(file_name, django_file, save=False)

        if commit:
            instance.save()
        return instance


class BackupRestoreRequestForm(forms.ModelForm):
    backup_file = forms.FileField(
        label="فایل بکاپ برای ریستور",
        required=True
    )

    class Meta:
        model = BackupRestoreRequest
        fields = ['backup_file']
