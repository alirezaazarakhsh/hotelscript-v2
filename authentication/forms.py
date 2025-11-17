from django import forms
from django.contrib.auth.models import Group
from .models import (
    Admin,
    JuridicalProfile,
    NaturalProfile,
)


class AdminForm(forms.ModelForm):
    # گروه‌های دسترسی (برای ادمین معمولی)
    admin_groups = forms.ModelMultipleChoiceField(
        label='گروه‌های دسترسی',
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'size': '10', 'style': 'min-height: 200px;'}),
        help_text='گروه‌های دسترسی برای این ادمین. اگر سوپر یوزر نباشد، فقط دسترسی‌های این گروه‌ها اعمال می‌شود.'
    )

    # رمز پنل (برای هر دو نوع ادمین)
    admin_password1 = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='رمز عبور برای ورود به پنل (هم پنل گرافیکی، هم پنل جنگو)'
    )
    admin_password2 = forms.CharField(
        label='تایید رمز عبور',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
    )

    # تبدیل به سوپر یوزر
    is_superuser = forms.BooleanField(
        label='سوپر یوزر (دسترسی کامل)',
        required=False,
        help_text='با تیک زدن، دسترسی کامل به تمام بخش‌ها. بدون تیک، فقط دسترسی‌های گروه‌های انتخابی.'
    )

    class Meta:
        model = Admin
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""
            # مقداردهی اولیه
            if self.instance.base_user_id:
                self.fields['admin_groups'].initial = self.instance.base_user.groups.all()
                self.fields['is_superuser'].initial = self.instance.base_user.is_superuser
                if self.instance.base_user.password:
                    self.fields['admin_password1'].help_text = '✓ رمز عبور تنظیم شده است.'

    def clean(self):
        cleaned = super().clean()
        # اعتبارسنجی رمز عبور
        p1 = cleaned.get('admin_password1')
        p2 = cleaned.get('admin_password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('admin_password2', 'رمزهای عبور مطابقت ندارند')
        
        return cleaned

    def save(self, commit=True):
        admin = super().save(commit=False)
        
        if commit:
            admin.save()

        # ذخیره گروه‌ها روی base_user
        groups = self.cleaned_data.get('admin_groups')
        if groups is not None and admin.base_user_id:
            admin.base_user.groups.set(groups)

        # تنظیم رمز عبور (هم برای پنل گرافیکی و هم برای پنل جنگو)
        password = self.cleaned_data.get('admin_password1')
        if password and admin.base_user:
            # رمز پنل گرافیکی
            admin.set_panel_password(password)
            admin.save(update_fields=['panel_password'])
            
            # رمز پنل جنگو
            admin.base_user.set_password(password)
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

