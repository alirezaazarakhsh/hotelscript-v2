from django import forms
from .models import Backup, AppModel, AppModule

class BackupForm(forms.ModelForm):
    class Meta:
        model = Backup
        fields = ['app', 'app_model', 'file', 'is_full_backup']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ابتدا همه مدل‌ها غیرفعال هستند تا وقتی اپلیکیشن انتخاب نشده
        self.fields['app_model'].queryset = AppModel.objects.none()

        if 'app' in self.data:
            try:
                app_id = int(self.data.get('app'))
                self.fields['app_model'].queryset = AppModel.objects.filter(app_id=app_id).order_by('name')
            except (ValueError, TypeError):
                pass  # داده نامعتبر است و queryset خالی می‌ماند

        elif self.instance.pk and self.instance.app:
            self.fields['app_model'].queryset = AppModel.objects.filter(app=self.instance.app).order_by('name')
