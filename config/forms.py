from django import forms
from .models import (
    SiteConfig,
    Slider,
)

class SiteConfigAdminForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SiteConfigAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['header_logo'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['header_logo'].help_text = f'<img src="{self.instance.header_logo.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.header_logo else ""

            self.fields['footer_logo'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['footer_logo'].help_text = f'<img src="{self.instance.footer_logo.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.footer_logo else ""

class SliderAdminForm(forms.ModelForm):
    class Meta:
        model = Slider
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SliderAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""
