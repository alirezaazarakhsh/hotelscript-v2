from django.contrib import admin
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import jdatetime
import qrcode
from io import BytesIO
import base64
import random
import string


# Unregister default admin if already registered
try:
    admin.site.unregister(TOTPDevice)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(StaticDevice)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(StaticToken)
except admin.sites.NotRegistered:
    pass


@admin.register(TOTPDevice)
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
        # اگر در حال ایجاد است (نه ویرایش)
        if not change:
            # تنظیم مقادیر پیش‌فرض
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
    
    class Meta:
        verbose_name = 'دستگاه TOTP'
        verbose_name_plural = 'دستگاه‌های TOTP (Google Authenticator)'


@admin.register(StaticDevice)
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
        """اگر کاربر جدید است و ادمین سایت است، 1 توکن 6 رقمی اتومات ایجاد کن"""
        is_new = not change
        super().save_model(request, obj, form, change)
        
        if is_new:
            # فقط برای کاربران ادمین (مدل Admin) یا superuser توکن ایجاد کن
            if obj.user.is_superuser or hasattr(obj.user, 'admin'):
                # تایید خودکار
                obj.confirmed = True
                obj.save()
                
                # ایجاد 1 توکن 6 رقمی
                token = ''.join(random.choices(string.digits, k=6))
                StaticToken.objects.create(device=obj, token=token)
    
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
        return format_html(f'<span style="font-weight: bold; background: #e8f5e9; padding: 5px 10px; border-radius: 3px;\">{count}</span>')
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
    
    class Meta:
        verbose_name = 'دستگاه توکن ثابت'
        verbose_name_plural = 'دستگاه‌های توکن ثابت'


@admin.register(StaticToken)
class StaticTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_user', 'token_preview', 'token_status', 'device_created_at_jalali')
    search_fields = ('device__user__phone_number', 'token')
    list_filter = ('device__confirmed',)
    ordering = ('-id',)
    readonly_fields = ('device_created_at_display', 'device')
    
    fieldsets = (
        ('اطلاعات دستگاه', {
            'fields': ('device',)
        }),
        ('توکن ثابت', {
            'fields': ('token',),
            'description': '<div style="color: #666; background: #f9f9f9; padding: 10px; border-radius: 5px;"><strong>راهنما:</strong> کد 6-8 رقمی را وارد کنید</div>'
        }),
        ('اطلاعات سیستم', {
            'fields': ('device_created_at_display',),
            'classes': ('collapse',),
        }),
    )
    
    def device_user(self, obj):
        return f"{obj.device.user.phone_number} ({obj.device.name})"
    device_user.short_description = 'کاربر / دستگاه'
    
    def token_preview(self, obj):
        return format_html(f'<code style="background: #f0f0f0; padding: 5px; border-radius: 3px; font-weight: bold;">{obj.token}</code>')
    token_preview.short_description = 'توکن ثابت'
    
    def token_status(self, obj):
        if obj.device.confirmed:
            return format_html('<span style="color: green; font-weight: bold;">✅ فعال</span>')
        return format_html('<span style="color: gray;">⏳ غیرفعال</span>')
    token_status.short_description = 'وضعیت'
    
    def device_created_at_jalali(self, obj):
        if obj.device and obj.device.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.device.created_at)
            return jalali_date.strftime("%Y/%m/%d - %H:%M:%S")
        return "-"
    device_created_at_jalali.short_description = 'تاریخ دستگاه'
    
    def device_created_at_display(self, obj):
        if obj.device and obj.device.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.device.created_at)
            gregorian = obj.device.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return format_html(
                '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
                f'<strong>🗓️ شمسی:</strong> {jalali_date.strftime("%Y/%m/%d - %H:%M:%S")}<br>'
                f'<strong>📅 میلادی:</strong> {gregorian}'
                '</div>'
            )
        return "-"
    device_created_at_display.short_description = 'تاریخ دستگاه'
    
    class Meta:
        verbose_name = 'توکن Static'
        verbose_name_plural = 'توکن‌های Static'


# Override app name in admin
from django.apps import apps
from django_otp.plugins.otp_totp import apps as totp_apps
from django_otp.plugins.otp_static import apps as static_apps

# Change verbose names for models and apps
TOTPDevice._meta.verbose_name = 'دستگاه TOTP'
TOTPDevice._meta.verbose_name_plural = 'دستگاه‌های TOTP (Google Authenticator)'

StaticDevice._meta.verbose_name = 'دستگاه توکن ثابت'
StaticDevice._meta.verbose_name_plural = 'دستگاه‌های توکن ثابت'

StaticToken._meta.verbose_name = 'توکن ثابت'
StaticToken._meta.verbose_name_plural = 'توکن‌های ثابت'

# Customize app names in admin
totp_app_config = apps.get_app_config('otp_totp')
totp_app_config.verbose_name = 'احراز هویت TOTP'

static_app_config = apps.get_app_config('otp_static')
static_app_config.verbose_name = 'احراز هویت توکن ثابت'
