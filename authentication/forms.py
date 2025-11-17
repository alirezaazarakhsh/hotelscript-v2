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

    # تبدیل به سوپر یوزر
    is_superuser = forms.BooleanField(
        label='دسترسی کامل (سوپر یوزر)',
        required=False,
        help_text='با تیک زدن، این ادمین به سوپر یوزر تبدیل می‌شود و به تمام بخش‌ها دسترسی کامل خواهد داشت. در غیر این صورت، فقط دسترسی‌های گروه‌های انتخابی را خواهد داشت.'
    )
    django_admin_password = forms.CharField(
        label='رمز پنل جنگو (برای سوپر یوزر)',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text='رمز عبور برای ورود به پنل جنگو (فقط در صورت تیک زدن دسترسی کامل الزامی است)'
    )

    # گروه‌های نقش (برای نقش ادمین سایت)
    admin_groups = forms.ModelMultipleChoiceField(
        label='گروه‌های نقش',
        queryset=Group.objects.all(),
        required=False,
        help_text='گروه‌های دسترسی (Role) برای این ادمین'
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
            # مقداردهی اولیه گروه‌ها و وضعیت سوپر یوزر از base_user
            if self.instance.base_user_id:
                self.fields['admin_groups'].initial = self.instance.base_user.groups.all()
                self.fields['is_superuser'].initial = self.instance.base_user.is_superuser
                if self.instance.base_user.password:
                    self.fields['django_admin_password'].help_text = '✓ رمز پنل جنگو تنظیم شده است. برای تغییر، رمز جدید وارد کنید.'

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('panel_password1')
        p2 = cleaned.get('panel_password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('panel_password2', 'رمزهای پنل گرافیکی مطابقت ندارند')

        is_su = cleaned.get('is_superuser')
        django_pwd = cleaned.get('django_admin_password')
        # اگر is_superuser تیک خورده و هنوز رمزی ذخیره نشده، رمز الزامی است
        if is_su and not django_pwd:
            if not (self.instance and self.instance.pk and self.instance.base_user and self.instance.base_user.password):
                self.add_error('django_admin_password', 'برای سوپر یوزر، وارد کردن رمز پنل جنگو الزامی است.')
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

        # تنظیم is_superuser و رمز جنگو
        is_su = self.cleaned_data.get('is_superuser', False)
        django_pwd = self.cleaned_data.get('django_admin_password')
        if admin.base_user:
            # به‌روزرسانی is_superuser
            if admin.base_user.is_superuser != is_su:
                admin.base_user.is_superuser = is_su
                admin.base_user.save(update_fields=["is_superuser"])
            # در صورت وارد کردن رمز جنگو، set_password
            if django_pwd:
                admin.base_user.set_password(django_pwd)
                admin.base_user.save(update_fields=["password"])

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

