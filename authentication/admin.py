from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.db.models import Q
from django_jalali.db import models as jmodels
from jalali_date.widgets import AdminJalaliDateWidget  
from django.utils.html import format_html
import jdatetime
from django.contrib.auth.models import Group
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
import qrcode
from io import BytesIO
import base64
import random
import string
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import (
    BaseUser,
    Admin,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
    CardNumber,
    JuridicalCardNumber,
    OTP,
    SMSPattern,
    GroupExtension,
)
from .forms import (
    AdminForm,
    JuridicalProfileForm,
    NaturalProfileForm,
)


# ==========================================
# فرم‌های سفارشی (Forms)
# ==========================================

class BaseUserChangeForm(forms.ModelForm):
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput,
        required=False,
        help_text="رمز عبور جدید را وارد کنید. اگر خالی بگذارید، رمز عبور تغییر نمی‌کند."
    )
    
    class Meta:
        model = BaseUser
        fields = ('phone_number',)
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            return password
        return self.instance.password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# ==========================================
# 01- کاربران پایه (BaseUser)
# ==========================================

@admin.register(BaseUser)
class BaseUserAdmin(admin.ModelAdmin):
    form = BaseUserChangeForm
    exclude = ('is_superuser', 'groups', 'user_permissions')
    
    list_display = (
        'id',
        'phone_number',
        'otp_status',
        'date_joined_jalali',
        'last_login_jalali',
        'user_type',
    )
    search_fields = ('phone_number',)
    ordering = ('-id',)
    list_filter = ('is_superuser',)
    actions = ['make_admin', 'setup_otp', 'recreate_otp', 'remove_otp', 'create_static_tokens']

    formfield_overrides = {
        jmodels.jDateTimeField: {'widget': AdminJalaliDateWidget},
    }

    readonly_fields = ('last_login', 'last_login_jalali', 'last_login_date', 'last_login_time', 'is_staff', 'otp_details', 'static_tokens_display', 'date_joined_jalali')
    
    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('phone_number', 'password'),
        }),
        ('تاریخ‌ها', {
            'fields': ('date_joined_jalali', 'last_login_jalali', 'last_login_date', 'last_login_time', 'last_login'),
            'classes': ('collapse',),
        }),
        ('احراز هویت TOTP', {
            'fields': ('otp_details',),
            'classes': ('collapse',),
        }),
        ('توکن‌های ثابت (کدهای پشتیبان)', {
            'fields': ('static_tokens_display',),
            'classes': ('collapse',),
        }),
    )
    
    def otp_status(self, obj):
        devices = TOTPDevice.objects.filter(user=obj, confirmed=True)
        if devices.exists():
            return format_html('<span style="color: green; font-weight: bold;">🔐 فعال</span>')
        return format_html('<span style="color: gray;">⚪ غیرفعال</span>')
    otp_status.short_description = 'وضعیت OTP'
    
    def otp_details(self, obj):
        devices = TOTPDevice.objects.filter(user=obj, confirmed=True)
        if not devices.exists():
            return format_html('<p style="color: gray;">❌ OTP فعال نیست</p>')
        
        html = '<div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">'
        html += '<h3>🔐 دستگاه‌های OTP فعال:</h3>'
        for device in devices:
            html += f'<div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px;">'
            html += f'<p><strong>Device ID:</strong> {device.id}</p>'
            html += f'<p><strong>نام:</strong> {device.name}</p>'
            html += f'<p><strong>Key:</strong> <code>{device.key}</code></p>'
            if hasattr(device, "created_at") and device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            else:
                html += f'<p><strong>تاریخ ایجاد:</strong> N/A</p>'
            
            uri = device.config_url
            qr = qrcode.QRCode(version=1, box_size=5, border=2)
            qr.add_data(uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            html += f'<p><strong>QR Code:</strong></p>'
            html += f'<img src="data:image/png;base64,{img_str}" style="width: 200px; height: 200px;" />'
            html += '</div>'
        html += '</div>'
        return format_html(html)
    otp_details.short_description = 'جزئیات OTP'
    
    def static_tokens_display(self, obj):
        static_devices = StaticDevice.objects.filter(user=obj, confirmed=True)
        if not static_devices.exists():
            return format_html('<p style="color: gray;">❌ هیچ توکن ثابتی وجود ندارد</p>')
        
        html = '<div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">'
        html += '<h3>📱 توکن‌های ثابت (کدهای پشتیبان):</h3>'
        for device in static_devices:
            tokens = device.token_set.all()
            html += f'<div style="margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 5px;">'
            html += f'<p><strong>نام دستگاه:</strong> {device.name}</p>'
            if device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            if tokens.exists():
                html += f'<p><strong>تعداد توکن‌های موجود:</strong> <span style="background: #e8f5e9; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{tokens.count()}</span></p>'
                html += '<div style="background: white; padding: 8px; border-radius: 3px; border-left: 3px solid #4CAF50;">'
                for idx, token in enumerate(tokens, 1):
                    html += f'<p style="margin: 4px 0;"><strong>توکن {idx}:</strong> <code style="background: #f0f0f0; padding: 4px 8px; border-radius: 2px; font-weight: bold; font-size: 14px;">{token.token}</code></p>'
                html += '</div>'
            else:
                html += f'<p style="color: orange;">⚠️ هیچ توکنی وجود ندارد</p>'
            html += '</div>'
        html += '</div>'
        return format_html(html)
    static_tokens_display.short_description = 'توکن‌های ثابت'
    
    def user_type(self, obj):
        if obj.is_superuser:
            return "🔴 ادمین جنگو"
        elif hasattr(obj, 'admin') and obj.admin:
            return "🟡 ادمین سایت"
        elif hasattr(obj, 'natural_profile') and obj.natural_profile:
            return "🟢 کاربر عادی"
        else:
            return "⚪ نامشخص"
    user_type.short_description = 'نوع کاربر'

    def date_joined_jalali(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    date_joined_jalali.short_description = 'تاریخ ثبت‌نام'

    def last_login_jalali(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    last_login_jalali.short_description = 'آخرین ورود'

    def last_login_date(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%Y/%m/%d')
        return "-"
    last_login_date.short_description = 'تاریخ آخرین ورود'

    def last_login_time(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%H:%M:%S')
        return "-"
    last_login_time.short_description = 'زمان آخرین ورود'

    def make_admin(self, request, queryset):
        created = 0
        for user in queryset:
            if not hasattr(user, 'admin') or user.admin is None:
                Admin.objects.create(
                    base_user=user,
                    first_name=getattr(user, 'first_name', '') or '',
                    last_name=getattr(user, 'last_name', '') or ''
                )
                created += 1
        self.message_user(request, f"{created} ادمین جدید ساخته شد.")
    make_admin.short_description = "تبدیل به ادمین سایت"
    
    def setup_otp(self, request, queryset):
        created = 0
        already_exists = 0
        for user in queryset:
            existing = TOTPDevice.objects.filter(user=user, confirmed=True)
            if existing.exists():
                already_exists += 1
                continue
            TOTPDevice.objects.create(user=user, name='default', confirmed=True)
            created += 1
        if created:
            self.message_user(request, f"✅ {created} OTP جدید ایجاد شد.")
        if already_exists:
            self.message_user(request, f"⚠️ {already_exists} کاربر از قبل OTP دارند.", level='warning')
    setup_otp.short_description = "🔐 فعال‌سازی OTP"
    
    def recreate_otp(self, request, queryset):
        recreated = 0
        for user in queryset:
            TOTPDevice.objects.filter(user=user).delete()
            TOTPDevice.objects.create(user=user, name='default', confirmed=True)
            recreated += 1
        self.message_user(request, f"✅ {recreated} OTP حذف و مجدداً ساخته شد.")
    recreate_otp.short_description = "🔄 ساخت مجدد OTP"
    
    def remove_otp(self, request, queryset):
        deleted = 0
        for user in queryset:
            count, _ = TOTPDevice.objects.filter(user=user).delete()
            deleted += count
        if deleted:
            self.message_user(request, f"✅ {deleted} OTP حذف شد.")
        else:
            self.message_user(request, "⚠️ هیچ OTP فعالی پیدا نشد.", level='warning')
    remove_otp.short_description = "🗑️ حذف OTP"
    
    def create_static_tokens(self, request, queryset):
        created = 0
        skipped = 0
        for user in queryset:
            if not (user.is_superuser or hasattr(user, 'admin')):
                skipped += 1
                continue
            device, is_new = StaticDevice.objects.get_or_create(user=user, defaults={'name': 'backup_codes', 'confirmed': True})
            device.token_set.all().delete()
            token = ''.join(random.choices(string.digits, k=6))
            StaticToken.objects.create(device=device, token=token)
            created += 1
        if created:
            self.message_user(request, f"✅ برای {created} کاربر ادمین توکن 6 رقمی ایجاد شد.")
        if skipped:
            self.message_user(request, f"⚠️ {skipped} کاربر عادی نادیده گرفته شد.", level='warning')
    create_static_tokens.short_description = "📱 ایجاد توکن ثابت 6 رقمی"


# ==========================================
# 02- مدیریت ادمین‌های سایت (Admin)
# ==========================================

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'id',
        'base_user_info',
        'admin_avatar',
        'otp_status',
        'get_groups',
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
    )
    autocomplete_fields = ['base_user']
    ordering = ('-id',)
    filter_horizontal = ('sms_patterns',)
    actions = ['setup_otp', 'recreate_otp', 'remove_otp']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('base_user', 'first_name', 'last_name', 'image', 'signature')
        }),
        ('دسترسی‌های پیامکی', {
            'fields': ('sms_patterns',),
        }),
        ('تنظیمات دسترسی', {
            'fields': ('admin_groups', 'is_superuser', 'admin_password1', 'admin_password2'),
            'description': 'گروه‌های دسترسی، سوپر یوزر و رمز عبور را در اینجا تنظیم کنید.',
        }),
        ('احراز هویت دو مرحله‌ای (OTP)', {
            'fields': ('otp_details',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('otp_details',)

    def base_user_info(self, obj):
        profile_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return f"{obj.base_user.phone_number} ({profile_name or 'بدون نام'})"
    base_user_info.short_description = 'موبایل و نام'

    def admin_avatar(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:50px; height:50px; border-radius:10%;" />', obj.image.url)
        return "—"
    admin_avatar.short_description = "عکس"
    
    def get_groups(self, obj):
        if obj.base_user.is_superuser:
            return format_html('<span style="color: red; font-weight: bold;">⭐ ادمین کل</span>')
        groups = obj.base_user.groups.all()
        if groups:
            return format_html('<br>'.join([f'🔹 {g.name}' for g in groups]))
        return "—"
    get_groups.short_description = 'گروه‌های دسترسی'
    
    def otp_status(self, obj):
        devices = TOTPDevice.objects.filter(user=obj.base_user, confirmed=True)
        if devices.exists():
            return format_html('<span style="color: green; font-weight: bold;">🔐 فعال</span>')
        return format_html('<span style="color: gray;">⚪ غیرفعال</span>')
    otp_status.short_description = 'وضعیت OTP'
    
    def otp_details(self, obj):
        devices = TOTPDevice.objects.filter(user=obj.base_user, confirmed=True)
        if not devices.exists():
            return format_html('<p style="color: gray;">❌ OTP فعال نیست</p>')
        
        html = '<div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">'
        html += '<h3>🔐 دستگاه‌های OTP فعال:</h3>'
        for device in devices:
            html += f'<div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px;">'
            html += f'<p><strong>Device ID:</strong> {device.id}</p>'
            html += f'<p><strong>نام:</strong> {device.name}</p>'
            html += f'<p><strong>Key:</strong> <code>{device.key}</code></p>'
            if hasattr(device, "created_at") and device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            else:
                html += f'<p><strong>تاریخ ایجاد:</strong> N/A</p>'
            
            uri = device.config_url
            qr = qrcode.QRCode(version=1, box_size=5, border=2)
            qr.add_data(uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            html += f'<p><strong>QR Code:</strong></p>'
            html += f'<img src="data:image/png;base64,{img_str}" style="width: 200px; height: 200px;" />'
            html += '</div>'
        html += '</div>'
        return format_html(html)
    otp_details.short_description = 'جزئیات OTP'
    
    def setup_otp(self, request, queryset):
        created = 0
        already_exists = 0
        for admin in queryset:
            existing = TOTPDevice.objects.filter(user=admin.base_user, confirmed=True)
            if existing.exists():
                already_exists += 1
                continue
            TOTPDevice.objects.create(user=admin.base_user, name='default', confirmed=True)
            created += 1
        if created:
            self.message_user(request, f"✅ {created} OTP جدید ایجاد شد.")
        if already_exists:
            self.message_user(request, f"⚠️ {already_exists} ادمین از قبل OTP دارند.", level='warning')
    setup_otp.short_description = "🔐 فعال‌سازی OTP"
    
    def recreate_otp(self, request, queryset):
        recreated = 0
        for admin in queryset:
            TOTPDevice.objects.filter(user=admin.base_user).delete()
            TOTPDevice.objects.create(user=admin.base_user, name='default', confirmed=True)
            recreated += 1
        self.message_user(request, f"✅ {recreated} OTP حذف و مجدداً ساخته شد.")
    recreate_otp.short_description = "🔄 ساخت مجدد OTP"
    
    def remove_otp(self, request, queryset):
        deleted = 0
        for admin in queryset:
            count, _ = TOTPDevice.objects.filter(user=admin.base_user).delete()
            deleted += count
        if deleted:
            self.message_user(request, f"✅ {deleted} OTP حذف شد.")
        else:
            self.message_user(request, "⚠️ هیچ OTP فعالی پیدا نشد.", level='warning')
    remove_otp.short_description = "🗑️ حذف OTP"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'base-user-autocomplete/',
                self.admin_site.admin_view(self.base_user_autocomplete),
                name='base_user_autocomplete',
            ),
        ]
        return custom_urls + urls

    def base_user_autocomplete(self, request):
        query = request.GET.get('q', '')
        users = BaseUser.objects.filter(
            Q(phone_number__icontains=query) |
            Q(natural_profile__first_name__icontains=query) |
            Q(natural_profile__last_name__icontains=query)
        )[:10]

        results = []
        for user in users:
            profile_name = ""
            if hasattr(user, 'natural_profile') and user.natural_profile:
                profile_name = f"{user.natural_profile.first_name or ''} {user.natural_profile.last_name or ''}".strip()
            results.append({
                'id': user.id,
                'text': f"{user.phone_number} ({profile_name})" if profile_name else user.phone_number
            })
        return JsonResponse({'results': results})


# ==========================================
# 03- پروفایل حقیقی کاربران
# ==========================================

class CardNumberInline(admin.TabularInline):
    model = CardNumber
    extra = 1
    max_num = 2
    fields = ('card_number', 'iban', 'account_holder_name')
    verbose_name = "شماره کارت حقیقی کاربر"
    verbose_name_plural = "شماره‌های کارت حقیقی کاربر"


@admin.register(NaturalProfile)
class NaturalProfileAdmin(admin.ModelAdmin):
    form = NaturalProfileForm
    list_display = (
        'id',
        'base_user__phone_number',
        'first_name',
        'last_name',
        'email',
        'national_code',
        'level',
        'total_purchase_formatted',
        'expiration_date',
        'auto_renewal_enabled',
        'manual_level_override',
        'subscription_package',
        'progress_target',
        'progress_deadline',
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
        'email',
        'national_code',
    )
    autocomplete_fields = ['base_user', 'level', 'previous_level']   
    ordering = ('-id',)
    inlines = [CardNumberInline]
    list_filter = ('level', 'expiration_date')
    readonly_fields = ('total_purchase', 'progress_target', 'progress_deadline')
    
    formfield_overrides = {
        jmodels.jDateField: {'widget': AdminJalaliDateWidget},
    }
    
    def total_purchase_formatted(self, obj):
        if obj.total_purchase:
            return f"{int(obj.total_purchase)} تومان"
        return "0 تومان"
    total_purchase_formatted.short_description = 'مجموع خرید'
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('base_user', 'first_name', 'last_name', 'email', 'national_code', 'image', 'postal_code', 'address')
        }),
        ('سطح کاربری', {
            'fields': ('level', 'total_purchase', 'expiration_date', 'previous_level', 'auto_renewal_enabled', 'manual_level_override', 'subscription_package', 'progress_target', 'progress_deadline'),
        }),
    )

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)


# ==========================================
# 04- پروفایل حقوقی
# ==========================================

class JuridicalProfileDocumentInline(admin.TabularInline):
    model = JuridicalProfileDocument
    extra = 3
    fields = ['file']
    verbose_name = 'مدرک پروفایل حقوقی'
    verbose_name_plural = 'مدارک پروفایل حقوقی'


class JuridicalCardNumberInline(admin.TabularInline):
    model = JuridicalCardNumber
    extra = 1
    max_num = 2
    fields = ('card_number', 'iban', 'account_holder_name')
    verbose_name = "شماره کارت حقوقی"
    verbose_name_plural = "شماره‌های کارت حقوقی"


@admin.register(JuridicalProfile)
class JuridicalProfileAdmin(admin.ModelAdmin):
    form = JuridicalProfileForm
    list_display = (
        'id',
        'get_base_user_phone_number',
        'organization_name',
        'national_id',
        'registration_number',
        'economical_code',
        'phone_number',
        'email',
        'status',
    )
    search_fields = (
        'organization_name',
        'national_id',
        'registration_number',
        'economical_code',
        'phone_number',
        'natural_profile__base_user__phone_number',
    )
    autocomplete_fields = ['natural_profile']
    ordering = ('-id',)
    inlines = [JuridicalProfileDocumentInline, JuridicalCardNumberInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('natural_profile', 'natural_profile__base_user')

    def get_base_user_phone_number(self, obj):
        try:
            if obj.natural_profile and obj.natural_profile.base_user:
                return obj.natural_profile.base_user.phone_number
        except Exception:
            pass
        return '-'
    get_base_user_phone_number.short_description = 'موبایل کاربر'


# ==========================================
# 08- رمز یک بار مصرف (OTP)
# ==========================================

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created')
    search_fields = ('user__phone_number',)
    ordering = ('-id',)


# پاکسازی ثبت‌های قبلی پروکسی‌ها
for model in [Group, TOTPDevice, StaticDevice, StaticToken]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


class GroupProxy(Group):
    class Meta:
        proxy = True
        app_label = 'authentication'
        verbose_name = '09- گروه دسترسی'
        verbose_name_plural = '09- گروه‌های دسترسی'


class TOTPDeviceProxy(TOTPDevice):
    class Meta:
        proxy = True
        app_label = 'authentication'
        verbose_name = '10- دستگاه TOTP'
        verbose_name_plural = '10- دستگاه‌های TOTP (Google Authenticator)'


class StaticDeviceProxy(StaticDevice):
    class Meta:
        proxy = True
        app_label = 'authentication'
        verbose_name = '11- دستگاه توکن ثابت'
        verbose_name_plural = '11- دستگاه‌های توکن ثابت'


class GroupExtensionInline(admin.StackedInline):
    model = GroupExtension
    extra = 0
    autocomplete_fields = ['icon']
    fields = ('icon', 'order', 'description')
    verbose_name = "تنظیمات گروه"
    verbose_name_plural = "تنظیمات گروه"
    classes = []


# ==========================================
# 09- گروه دسترسی
# ==========================================
@admin.register(GroupProxy)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "get_icon", "get_order", "admin_members_count")
    search_fields = ("name", "extension__display_name")
    ordering = ("extension__order", "name")
    inlines = [GroupExtensionInline]
    filter_horizontal = ('permissions',)
    
    def get_icon(self, obj):
        try:
            if obj.extension.icon:
                return obj.extension.icon.title_icon
        except GroupExtension.DoesNotExist:
            pass
        return "—"
    get_icon.short_description = "آیکون"
    
    def get_order(self, obj):
        try:
            return obj.extension.order
        except GroupExtension.DoesNotExist:
            return 0
    get_order.short_description = "ترتیب"

    def admin_members_count(self, obj):
        return BaseUser.objects.filter(groups=obj, admin__isnull=False).count()
    admin_members_count.short_description = "تعداد ادمین‌های سایت"


# ==========================================
# 10- دستگاه TOTP
# ==========================================
@admin.register(TOTPDeviceProxy)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_phone', 'name', 'confirmed_status', 'created_at_jalali')
    search_fields = ('user__phone_number',)
    list_filter = ('confirmed',)
    ordering = ('-id',)
    autocomplete_fields = ['user']
    readonly_fields = ('key', 'created_at', 'qr_code_display', 'name', 'confirmed')
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('user',)
        }),
        ('اطلاعات دستگاه (اتومات)', {
            'fields': ('name', 'confirmed', 'key', 'created_at'),
            'classes': ('collapse',),
        }),
        ('QR Code', {
            'fields': ('qr_code_display',),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.name:
                obj.name = 'default'
            obj.confirmed = True
        super().save_model(request, obj, form, change)
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'شماره کاربر'
    
    def confirmed_status(self, obj):
        if obj.confirmed:
            return format_html('<span style="color: green; font-weight: bold;">✅ تایید شده</span>')
        return format_html('<span style="color: orange;">⏳ در انتظار تایید</span>')
    confirmed_status.short_description = 'وضعیت'
    
    def created_at_jalali(self, obj):
        if obj.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
        return "-"
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def qr_code_display(self, obj):
        if not obj.confirmed:
            return format_html('<p style="color: orange;">⏳ دستگاه هنوز تایید نشده</p>')
        
        uri = obj.config_url
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        html = '<div style="text-align: center;">'
        html += f'<p><strong>QR Code برای Google Authenticator:</strong></p>'
        html += f'<img src="data:image/png;base64,{img_str}" style="width: 250px; height: 250px; border: 1px solid #ddd; padding: 10px;" />'
        html += f'<p><strong>Key:</strong> <code style="background: #f5f5f5; padding: 5px;">{obj.key}</code></p>'
        html += '</div>'
        return format_html(html)
    qr_code_display.short_description = 'نمایش QR Code'


# ==========================================
# 11- دستگاه توکن ثابت
# ==========================================
@admin.register(StaticDeviceProxy)
class StaticDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_phone', 'name', 'confirmed_status', 'token_count', 'created_at_jalali')
    search_fields = ('user__phone_number', 'name')
    list_filter = ('confirmed',)
    ordering = ('-id',)
    autocomplete_fields = ['user']
    readonly_fields = ('created_at_display', 'token_list_display')
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('user', 'name')
        }),
        ('تنظیمات', {
            'fields': ('confirmed',)
        }),
        ('توکن‌های ایجاد شده', {
            'fields': ('token_list_display',),
            'classes': ('collapse',),
        }),
        ('اطلاعات سیستم', {
            'fields': ('created_at_display',),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        is_new = not change
        super().save_model(request, obj, form, change)
        
        if is_new:
            if obj.user.is_superuser or hasattr(obj.user, 'admin'):
                obj.confirmed = True
                obj.save()
                token = ''.join(random.choices(string.digits, k=6))
                StaticToken.objects.create(device_id=obj.id, token=token)
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'شماره کاربر'
    
    def confirmed_status(self, obj):
        if obj.confirmed:
            return format_html('<span style="color: green; font-weight: bold;">✅ فعال</span>')
        return format_html('<span style="color: orange;">⏳ غیرفعال</span>')
    confirmed_status.short_description = 'وضعیت'
    
    def token_count(self, obj):
        count = obj.token_set.count()
        return format_html(f'<span style="font-weight: bold; background: #e8f5e9; padding: 5px 10px; border-radius: 3px;">{count}</span>')
    token_count.short_description = 'تعداد توکن'
    
    def created_at_jalali(self, obj):
        if obj.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
        return "-"
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def created_at_display(self, obj):
        if obj.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            gregorian = obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return format_html(
                '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
                f'<strong>🗓️ شمسی:</strong> {jalali_date.strftime("%Y/%m/%d - %H:%M:%S")}<br>'
                f'<strong>📅 میلادی:</strong> {gregorian}'
                '</div>'
            )
        return "-"
    created_at_display.short_description = 'تاریخ ایجاد'
    
    def token_list_display(self, obj):
        tokens = obj.token_set.all()
        if not tokens.exists():
            return format_html('<p style="color: #999;">هیچ توکنی ایجاد نشده</p>')
        
        html = '<div style="background: #f9f9f9; padding: 10px; border-radius: 5px;">'
        for idx, token in enumerate(tokens, 1):
            html += f'<p><strong>توکن {idx}:</strong> <code style="background: white; padding: 5px; border-radius: 3px; font-weight: bold;">{token.token}</code></p>'
        html += '</div>'
        return format_html(html)
    token_list_display.short_description = 'توکن‌های ثابت'


# ==========================================
# TinyMCE Upload View
# ==========================================

def tinymce_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        file_name = default_storage.save(f'tinymce/{file.name}', ContentFile(file.read()))
        file_url = default_storage.url(file_name)
        return JsonResponse({'location': file_url})
    return JsonResponse({'error': 'Invalid request'}, status=400)