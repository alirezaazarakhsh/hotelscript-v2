from django import forms
from django.contrib.auth.models import Group
from .models import (
    Admin,
    JuridicalProfile,
    NaturalProfile,
)


class AdminForm(forms.ModelForm):
    # پنل گرافیکی
    panel_password1 = forms.CharField(
        label='رمز پنل گرافیکی',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='برای تنظیم یا تغییر رمز پنل گرافیکی ادمین'
    )
    panel_password2 = forms.CharField(
        label='تایید رمز پنل گرافیکی',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='تایید رمز پنل گرافیکی'
    )

    # گروه‌های دسترسی
    admin_groups = forms.ModelMultipleChoiceField(
        label='گروه‌های دسترسی',
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='گروه‌های دسترسی برای این ادمین را انتخاب کنید (مثل گروه بلاگ، گروه مالی و ...)'
    )

    class Meta:
        model = Admin
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""
            if self.instance.panel_password:
                self.fields['panel_password1'].help_text = '✓ رمز پنل گرافیکی تنظیم شده است. برای تغییر، رمز جدید وارد کنید.'
            # مقداردهی اولیه گروه‌ها از base_user
            if self.instance.base_user_id:
                self.fields['admin_groups'].initial = self.instance.base_user.groups.all()

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('panel_password1')
        p2 = cleaned.get('panel_password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('panel_password2', 'رمزهای پنل گرافیکی مطابقت ندارند')
        return cleaned

    def save(self, commit=True):
        admin = super().save(commit=False)
        # تنظیم رمز پنل گرافیکی
        panel_pwd = self.cleaned_data.get('panel_password1')
        if panel_pwd:
            admin.set_panel_password(panel_pwd)
        if commit:
            admin.save()

        # ذخیره گروه‌ها روی base_user
        groups = self.cleaned_data.get('admin_groups')
        if groups is not None and admin.base_user_id:
            admin.base_user.groups.set(groups)

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

