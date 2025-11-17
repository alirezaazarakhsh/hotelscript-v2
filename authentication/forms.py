from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import (
    Admin,
    JuridicalProfile,
    NaturalProfile,
)


class AdminForm(forms.ModelForm):
    password1 = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='رمز عبور برای ورود به پنل ادمین جنگو. خالی بگذارید اگر نمی‌خواهید تغییر دهید.'
    )
    password2 = forms.CharField(
        label='تایید رمز عبور',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='برای تایید، رمز عبور را دوباره وارد کنید.'
    )
    
    class Meta:
        model = Admin
        exclude = ['password']

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""
            # نمایش پیام برای رمز عبور موجود
            if self.instance.password:
                self.fields['password1'].help_text = '✓ رمز عبور تنظیم شده است. برای تغییر، رمز جدید وارد کنید.'
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("رمزهای عبور مطابقت ندارند")
        return password2

    def save(self, commit=True):
        admin = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            admin.set_password(password)
        if commit:
            admin.save()
        return admin



class NaturalProfileForm(forms.ModelForm):
    class Meta:
        model = NaturalProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(NaturalProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""



class JuridicalProfileForm(forms.ModelForm):
    class Meta:
        model = JuridicalProfile
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super(JuridicalProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

