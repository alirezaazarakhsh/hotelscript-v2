from django import forms
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

    class Meta:
        model = BackupLog
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ─────── model_name choices handling ───────
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

        # ─────── file_path dropdown handling ───────
        backup_folder = os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')
        if os.path.exists(backup_folder):
            file_choices = [
                (os.path.join(backup_folder, f), f)
                for f in os.listdir(backup_folder)
                if os.path.isfile(os.path.join(backup_folder, f))
            ]
            self.fields['file_path'] = forms.ChoiceField(
                choices=file_choices,
                required=False,
                label="فایل بکاپ"
            )
        else:
            self.fields['file_path'] = forms.ChoiceField(
                choices=[],
                required=False,
                label="فایل بکاپ (پوشه پیدا نشد)"
            )



class BackupRestoreRequestForm(forms.ModelForm):
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