from django import forms
from .models import (
    Admin,
    NaturalProfile,
)

class AdminForm(forms.ModelForm):
    class Meta:
        model = Admin
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

            self.fields['signature'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['signature'].help_text = f'<img src="{self.instance.signature.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.signature else ""

class NaturalProfileForm(forms.ModelForm):
    class Meta:
        model = NaturalProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(NaturalProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""
