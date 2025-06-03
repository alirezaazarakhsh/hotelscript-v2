import os
from django import forms
from django.core.files import File
from safarname24 import settings
from .models import BackupLog, BackupRestoreRequest
from .apps_models_list import APPS_MODELS


class DynamicAppModelMixin:
    def set_model_name_choices(self, field_key='model_name'):
        selected_app = self.data.get('app_name') or getattr(self.instance, 'app_name', None)

        if selected_app in APPS_MODELS:
            self.fields[field_key].choices = [(m, m) for m in APPS_MODELS[selected_app]]
            self.fields[field_key].widget.attrs.pop('disabled', None)
        else:
            self.fields[field_key].choices = []
            self.fields[field_key].widget.attrs['disabled'] = True


class BackupLogAdminForm(forms.ModelForm, DynamicAppModelMixin):
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
    file_choice = forms.ChoiceField(
        choices=[],
        label="انتخاب فایل بکاپ از مسیر محلی",
        required=False,
        help_text="در صورت انتخاب فایل، در فیلد backup_file آپلود می‌شود."
    )

    class Meta:
        model = BackupLog
        fields = ['backup_type', 'app_name', 'model_name', 'backup_file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_model_name_choices()

        # بارگذاری فایل‌ها از پوشه local
        backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
        file_choices = []

        if os.path.exists(backup_folder) and os.path.isdir(backup_folder):
            file_choices = [
                (f, f)
                for f in os.listdir(backup_folder)
                if os.path.isfile(os.path.join(backup_folder, f))
            ]
        if file_choices:
            self.fields['file_choice'].choices = file_choices
        else:
            self.fields['file_choice'].choices = []
            self.fields['file_choice'].widget.attrs['disabled'] = True
            self.fields['file_choice'].help_text = "فایلی در پوشه بکاپ پیدا نشد."

    def clean(self):
        cleaned_data = super().clean()
        file_choice = cleaned_data.get('file_choice')

        if file_choice:
            backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
            full_path = os.path.join(backup_folder, file_choice)

            if not os.path.exists(full_path):
                raise forms.ValidationError("فایل انتخاب‌شده در مسیر بکاپ وجود ندارد.")

            with open(full_path, 'rb') as f:
                self.cleaned_data['backup_file'] = File(f, name=file_choice)

        return cleaned_data


class BackupRestoreRequestForm(forms.ModelForm, DynamicAppModelMixin):
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

    class Meta:
        model = BackupRestoreRequest
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_model_name_choices()
