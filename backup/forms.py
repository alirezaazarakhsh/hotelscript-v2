# forms.py در اپلیکیشن backup
from django import forms
from .apps_models_list import APPS_MODELS

class BackupCreationForm(forms.Form):
    backup_type = forms.ChoiceField(choices=[('full', 'Full Project'), ('app', 'App Only'), ('model', 'Single Model')])
    app_name = forms.ChoiceField(required=False)
    model_name = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['app_name'].choices = [('', '---------')] + [(app, app.title()) for app in APPS_MODELS]
        self.fields['model_name'].choices = [('', '---------')]  # filled dynamically via JS

    class Media:
        js = ('admin/js/backup_form.js',)  # فایل جاوااسکریپت برای داینامیک کردن مدل‌ها
