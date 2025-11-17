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
        help_text='رمز برای ورود به پنل گرافیکی'
    )
    panel_password2 = forms.CharField(
        label='تایید رمز پنل گرافیکی',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
    )

    # رمز پنل جنگو (برای هر دو نوع ادمین)
    django_admin_password1 = forms.CharField(
        label='رمز پنل جنگو',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='رمز برای ورود به پنل جنگو (برای ادمین معمولی و سوپر یوزر)'
    )
    django_admin_password2 = forms.CharField(
        label='تایید رمز پنل جنگو',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
    )

    # تبدیل به سوپر یوزر (دسترسی کامل)
    is_superuser = forms.BooleanField(
        label='سوپر یوزر (دسترسی کامل)',
        required=False,
        help_text='با تیک زدن، دسترسی کامل به تمام بخش‌ها. بدون تیک، فقط دسترسی‌های گروه‌ها اعمال می‌شود.'
    )

    # گروه‌های دسترسی (برای ادمین معمولی)
    admin_groups = forms.ModelMultipleChoiceField(
        label='گروه‌های دسترسی',
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='گروه‌های دسترسی برای این ادمین (مثل گروه بلاگ، مالی، رزرواسیون و ...)'
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
                self.fields['panel_password1'].help_text = '✓ رمز پنل گرافیکی تنظیم شده است.'
            # مقداردهی اولیه
            if self.instance.base_user_id:
                self.fields['admin_groups'].initial = self.instance.base_user.groups.all()
                self.fields['is_superuser'].initial = self.instance.base_user.is_superuser
                if self.instance.base_user.password:
                    self.fields['django_admin_password1'].help_text = '✓ رمز پنل جنگو تنظیم شده است.'

    def clean(self):
        cleaned = super().clean()
        # اعتبارسنجی رمز پنل گرافیکی
        p1 = cleaned.get('panel_password1')
        p2 = cleaned.get('panel_password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('panel_password2', 'رمزهای پنل گرافیکی مطابقت ندارند')

        # اعتبارسنجی رمز پنل جنگو
        d1 = cleaned.get('django_admin_password1')
        d2 = cleaned.get('django_admin_password2')
        if (d1 or d2) and d1 != d2:
            self.add_error('django_admin_password2', 'رمزهای پنل جنگو مطابقت ندارند')
        
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

        # تنظیم رمز پنل جنگو (برای هر دو نوع ادمین)
        django_pwd = self.cleaned_data.get('django_admin_password1')
        if django_pwd and admin.base_user:
            admin.base_user.set_password(django_pwd)
            admin.base_user.save(update_fields=["password"])

        # تنظیم is_superuser
        is_su = self.cleaned_data.get('is_superuser', False)
        if admin.base_user and admin.base_user.is_superuser != is_su:
            admin.base_user.is_superuser = is_su
            admin.base_user.save(update_fields=["is_superuser"])

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

