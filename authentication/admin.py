# admin.py
from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.db.models import Q
from django_jalali.db import models as jmodels
from jalali_date.widgets import AdminJalaliDateWidget  
from django.utils.html import format_html
from django.utils import timezone  
import jdatetime
from django.contrib.auth.models import Group
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
import qrcode
from io import BytesIO
import base64
import random
import string
from .models import (
    BaseUser,
    Admin,
    CardNumber,
    JuridicalCardNumber,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
    OTP,
    SMSPattern,
    GroupExtension,
)
from .forms import (
    AdminForm,
    JuridicalProfileForm,
    NaturalProfileForm,
)


# فرم سفارشی برای BaseUser برای مدیریت رمز عبور
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
            # اگر رمز عبور جدید وارد شد، آن را تایید کن
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


# فرم سفارشی برای اینلاین پترن‌های پیامکی
class AdminSMSPatternInlineForm(forms.ModelForm):
    class Meta:
        model = Admin.sms_patterns.through
        fields = ('smspattern',)  # استفاده از نام فیلد صحیح در جدول واسطه

    smspattern = forms.ModelChoiceField(
        queryset=SMSPattern.objects.all(),
        label="پترن پیامکی",
        to_field_name="id",
    )

# اینلاین برای نمایش و ویرایش پترن‌های پیامکی
# class AdminSMSPatternInline(admin.TabularInline):
#     model = Admin.sms_patterns.through
#     form = AdminSMSPatternInlineForm
#     verbose_name = "پترن پیامکی"
#     verbose_name_plural = "پترن‌های پیامکی"
#     extra = 1

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
    
    # امکان تنظیم گروه‌ها و دسترسی‌ها برای ادمین
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
        # اگر سوپر یوزر باشد
        if obj.base_user.is_superuser:
            return format_html('<span style="color: red; font-weight: bold;">⭐ ادمین کل</span>')
        
        # در غیر این صورت گروه‌ها
        groups = obj.base_user.groups.all()
        if groups:
            return format_html('<br>'.join([f'🔹 {g.name}' for g in groups]))
        return "—"
    get_groups.short_description = 'گروه‌های دسترسی'
    
    # نمایش وضعیت OTP
    def otp_status(self, obj):
        devices = TOTPDevice.objects.filter(user=obj.base_user, confirmed=True)
        if devices.exists():
            return format_html('<span style="color: green; font-weight: bold;">🔐 فعال</span>')
        return format_html('<span style="color: gray;">⚪ غیرفعال</span>')
    otp_status.short_description = 'وضعیت OTP'
    
    # نمایش جزئیات OTP در صفحه ویرایش
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
            
            # تبدیل تاریخ میلادی به شمسی
            if hasattr(device, "created_at") and device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            else:
                html += f'<p><strong>تاریخ ایجاد:</strong> N/A</p>'
            
            # نمایش QR Code
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
            
            TOTPDevice.objects.create(
                user=admin.base_user,
                name='default',
                confirmed=True
            )
            created += 1
        
        if created:
            self.message_user(request, f"✅ {created} OTP جدید ایجاد شد.")
        if already_exists:
            self.message_user(request, f"⚠️ {already_exists} ادمین از قبل OTP دارند. از 'ساخت مجدد OTP' استفاده کنید.", level='warning')
    setup_otp.short_description = "🔐 فعال‌سازی OTP (فقط برای ادمین‌های بدون OTP)"
    
    def recreate_otp(self, request, queryset):
        recreated = 0
        
        for admin in queryset:
            # حذف OTP های قبلی
            TOTPDevice.objects.filter(user=admin.base_user).delete()
            
            # ایجاد OTP جدید
            TOTPDevice.objects.create(
                user=admin.base_user,
                name='default',
                confirmed=True
            )
            recreated += 1
        
        self.message_user(request, f"✅ {recreated} OTP حذف و مجدداً ساخته شد. QR code های جدید را اسکن کنید.")
    recreate_otp.short_description = "🔄 ساخت مجدد OTP (حذف قبلی + ایجاد جدید)"
    
    def remove_otp(self, request, queryset):
        deleted = 0
        
        for admin in queryset:
            count, _ = TOTPDevice.objects.filter(user=admin.base_user).delete()
            deleted += count
        
        if deleted:
            self.message_user(request, f"✅ {deleted} OTP حذف شد.")
        else:
            self.message_user(request, "⚠️ هیچ OTP فعالی برای حذف پیدا نشد.", level='warning')
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
    
    


# مدل SuperUser حذف شد - اکنون از فیلد is_superuser در BaseUser استفاده می‌شود

# سفارشی‌سازی نمایش گروه‌ها
try:
    admin.site.unregister(Group)
except Exception:
    pass


# Inline برای تنظیمات گروه (بدون accordion)
class GroupExtensionInline(admin.StackedInline):
    model = GroupExtension
    extra = 0
    autocomplete_fields = ['icon']
    fields = ('icon', 'order', 'description')
    verbose_name = "تنظیمات گروه"
    verbose_name_plural = "تنظیمات گروه"
    
    # حذف classes برای غیرفعال کردن accordion
    classes = []


@admin.register(Group)
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
    
    # حذف filter_horizontal برای BaseUser - فقط برای ادمین‌ها نیاز است
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
    
    # نمایش وضعیت OTP
    def otp_status(self, obj):
        devices = TOTPDevice.objects.filter(user=obj, confirmed=True)
        if devices.exists():
            return format_html('<span style="color: green; font-weight: bold;">🔐 فعال</span>')
        return format_html('<span style="color: gray;">⚪ غیرفعال</span>')
    otp_status.short_description = 'وضعیت OTP'
    
    # نمایش جزئیات OTP در صفحه ویرایش
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
            
            # تبدیل تاریخ میلادی به شمسی
            if hasattr(device, "created_at") and device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            else:
                html += f'<p><strong>تاریخ ایجاد:</strong> N/A</p>'
            
            # نمایش QR Code
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
        """نمایش توکن‌های ثابت کاربر"""
        static_devices = StaticDevice.objects.filter(user=obj, confirmed=True)
        
        if not static_devices.exists():
            return format_html('<p style="color: gray;">❌ هیچ توکن ثابتی وجود ندارد</p>')
        
        html = '<div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">'
        html += '<h3>📱 توکن‌های ثابت (کدهای پشتیبان):</h3>'
        
        for device in static_devices:
            tokens = device.token_set.all()
            
            html += f'<div style="margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 5px;">'
            html += f'<p><strong>نام دستگاه:</strong> {device.name}</p>'
            
            # تاریخ ایجاد دستگاه
            if device.created_at:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=device.created_at)
                date_str = jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
                html += f'<p><strong>تاریخ ایجاد:</strong> {date_str}</p>'
            
            # نمایش توکن‌ها
            if tokens.exists():
                html += f'<p><strong>تعداد توکن‌های موجود:</strong> <span style="background: #e8f5e9; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{tokens.count()}</span></p>'
                html += '<div style="background: white; padding: 8px; border-radius: 3px; border-left: 3px solid #4CAF50;">'
                for idx, token in enumerate(tokens, 1):
                    html += f'<p style="margin: 4px 0;"><strong>توکن {idx}:</strong> <code style="background: #f0f0f0; padding: 4px 8px; border-radius: 2px; font-weight: bold; font-size: 14px;">{token.token}</code></p>'
                html += '</div>'
            else:
                html += f'<p style="color: orange;">⚠️ هیچ توکنی برای این دستگاه وجود ندارد</p>'
            
            html += '</div>'
        
        html += '</div>'
        return format_html(html)
    static_tokens_display.short_description = 'توکن‌های ثابت'
    
    # نمایش نوع کاربر
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
            
            TOTPDevice.objects.create(
                user=user,
                name='default',
                confirmed=True
            )
            created += 1
        
        if created:
            self.message_user(request, f"✅ {created} OTP جدید ایجاد شد.")
        if already_exists:
            self.message_user(request, f"⚠️ {already_exists} کاربر از قبل OTP دارند. از 'ساخت مجدد OTP' استفاده کنید.", level='warning')
    setup_otp.short_description = "🔐 فعال‌سازی OTP (فقط برای کاربران بدون OTP)"
    
    def recreate_otp(self, request, queryset):
        recreated = 0
        
        for user in queryset:
            # حذف OTP های قبلی
            TOTPDevice.objects.filter(user=user).delete()
            
            # ایجاد OTP جدید
            TOTPDevice.objects.create(
                user=user,
                name='default',
                confirmed=True
            )
            recreated += 1
        
        self.message_user(request, f"✅ {recreated} OTP حذف و مجدداً ساخته شد. QR code های جدید را اسکن کنید.")
    recreate_otp.short_description = "🔄 ساخت مجدد OTP (حذف قبلی + ایجاد جدید)"
    
    def remove_otp(self, request, queryset):
        deleted = 0
        
        for user in queryset:
            count, _ = TOTPDevice.objects.filter(user=user).delete()
            deleted += count
        
        if deleted:
            self.message_user(request, f"✅ {deleted} OTP حذف شد.")
        else:
            self.message_user(request, "⚠️ هیچ OTP فعالی برای حذف پیدا نشد.", level='warning')
    remove_otp.short_description = "🗑️ حذف OTP"
    
    def create_static_tokens(self, request, queryset):
        """ایجاد توکن ثابت 6 رقمی فقط برای ادمین‌های سایت"""
        created = 0
        skipped = 0
        
        for user in queryset:
            # فقط ادمین‌های سایت (مدل Admin) یا superuser می‌تونند توکن داشته باشند
            if not (user.is_superuser or hasattr(user, 'admin')):
                skipped += 1
                continue
            
            # بررسی وجود StaticDevice
            device, is_new = StaticDevice.objects.get_or_create(user=user, defaults={'name': 'backup_codes', 'confirmed': True})
            
            # حذف توکن‌های قدیمی و ایجاد توکن جدید
            device.token_set.all().delete()
            
            # ایجاد 1 توکن 6 رقمی
            token = ''.join(random.choices(string.digits, k=6))
            StaticToken.objects.create(device=device, token=token)
            
            created += 1
        
        if created:
            self.message_user(request, f"✅ برای {created} کاربر ادمین 1 توکن 6 رقمی ایجاد شد.")
        if skipped:
            self.message_user(request, f"⚠️ {skipped} کاربر عادی در لیست بود و نادیده گرفته شدند (فقط برای ادمین‌های سایت).", level='warning')
    create_static_tokens.short_description = "📱 ایجاد توکن ثابت 6 رقمی (فقط برای ادمین‌های سایت)"
    


class CardNumberInline(admin.TabularInline):
    model = CardNumber
    extra = 1  # نمایش یک فرم خالی
    max_num = 2  # محدودیت حداکثر ۲ شماره کارت
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
    readonly_fields = ('total_purchase', 'progress_target', 'progress_deadline')  # مجموع خرید فقط خواندنی
    
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
            'description': 'سطح کاربری کاربر. expiration_date برای سطوح موقتی (مثل خرید پکیج). previous_level سطح قبلی قبل از ارتقای موقتی. manual_level_override برای جلوگیری از آپدیت خودکار سطح بر اساس خرید.',
        }),
    )

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

    def save_related(self, request, form, formsets, change):
        
        super().save_related(request, form, formsets, change)

        for formset in formsets:
            self.save_formset(request, form, formset, change=change)




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
        'get_natural_profile_first_name',
        'get_natural_profile_last_name',
        'organization_name',
        'national_id',
        'registeration_number',
        'economical_code',
        'phone_number',
        'email',
        'status',
    )
    search_fields = (
        'natural_profile__base_user__phone_number',
        'natural_profile__first_name',
        'natural_profile__last_name',
        'organization_name',
        'national_id',
        'registeration_number',
        'economical_code',
        'phone_number',
    )
    autocomplete_fields = ['natural_profile']
    ordering = ('-id',)
    inlines = [JuridicalProfileDocumentInline, JuridicalCardNumberInline]

    def get_queryset(self, request):
        # فقط یک سطح select_related انجام می‌دهیم
        return super().get_queryset(request).select_related('natural_profile', 'natural_profile__base_user')

    def get_base_user_phone_number(self, obj):
        if obj.pk and obj.natural_profile and obj.natural_profile.base_user:
            return obj.natural_profile.base_user.phone_number
        return ''
    get_base_user_phone_number.short_description = 'موبایل'

    def get_natural_profile_first_name(self, obj):
        if obj.pk and obj.natural_profile:
            return obj.natural_profile.first_name
        return ''
    get_natural_profile_first_name.short_description = 'نام'

    def get_natural_profile_last_name(self, obj):
        if obj.pk and obj.natural_profile:
            return obj.natural_profile.last_name
        return ''
    get_natural_profile_last_name.short_description = 'نام خانوادگی'

    
    
    
@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'code',
        'created',
    )
    search_fields = (
        'user',
    )
    ordering = (
        '-id',
    )


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

@csrf_exempt
def tinymce_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        # ذخیره فایل در media
        file_name = default_storage.save(f'tinymce/{file.name}', ContentFile(file.read()))
        file_url = default_storage.url(file_name)
        return JsonResponse({'location': file_url})
    return JsonResponse({'error': 'Invalid request'}, status=400)