from django import forms
from .models import BackupLog
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

        selected_app = None
        # اگر فرم داده ارسال شده
        if 'app_name' in self.data:
            selected_app = self.data.get('app_name')
        # اگر شی مدل داریم (مثلاً ویرایش)
        elif self.instance and self.instance.app_name:
            selected_app = self.instance.app_name

        if selected_app in APPS_MODELS:
            model_choices = [(m, m) for m in APPS_MODELS[selected_app]]
            self.fields['model_name'].choices = model_choices
            self.fields['model_name'].widget.attrs.pop('disabled', None)
        else:
            self.fields['model_name'].choices = []
            self.fields['model_name'].widget.attrs['disabled'] = True
