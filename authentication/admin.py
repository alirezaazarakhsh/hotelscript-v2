# admin.py
from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
from django_jalali.db import models as jmodels
from jalali_date.widgets import AdminJalaliDateWidget  
from django.utils.html import format_html
from django.utils import timezone  
import jdatetime
from .models import (
    BaseUser,
    Admin,
    CardNumber,
    JuridicalCardNumber,
    SuperUser,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
    OTP,
    SMSPattern,
)
from .forms import (
    AdminForm,
    JuridicalProfileForm,
    NaturalProfileForm,
)


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
        'admin_avatar',   # 👈 نمایش عکس پروفایل
       
    )
    search_fields = (
        'base_user__phone_number',
        
    )
    autocomplete_fields = ['base_user']
    ordering = ('-id',)

    def base_user_info(self, obj):
        profile_name = ""
        if hasattr(obj.base_user, 'natural_profile') and obj.base_user.natural_profile:
            profile_name = f"{obj.base_user.natural_profile.first_name or ''} {obj.base_user.natural_profile.last_name or ''}".strip()
        return f"{obj.base_user.phone_number} ({profile_name or 'پروفایل موجود نیست'})"
    base_user_info.short_description = 'موبایل و نام'

    def admin_avatar(self, obj):
        if obj.image:  # 👈 فرض بر این است فیلد image در مدل Admin وجود دارد
            return format_html('<img src="{}" style="width:50px; height:50px; border-radius:10%;" />', obj.image.url)
        return "—"
    admin_avatar.short_description = "عکس پروفایل"

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
    
    


@admin.register(BaseUser)
class BaseUserAdmin(admin.ModelAdmin):
    exclude = ('is_superuser',)
    
    list_display = (
        'id',
        'phone_number',
        'date_joined_jalali',
        'last_login_jalali',
    )
    
    search_fields = ('phone_number',)
    ordering = ('-id',)

    formfield_overrides = {
        jmodels.jDateTimeField: {'widget': AdminJalaliDateWidget},
    }

    readonly_fields = ('last_login_date', 'last_login_time')

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
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
        'email',
        'national_code',
    )
    autocomplete_fields = ['base_user']   
    ordering = ('-id',)
    inlines = [CardNumberInline]

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
    extra = 1  # نمایش یک فرم خالی برای افزودن شماره کارت جدید
    max_num = 2  # محدودیت حداکثر ۲ شماره کارت
    fields = ('card_number', 'iban' , 'account_holder_name')  # فیلدهای قابل ویرایش در اینلاین
    verbose_name = "شماره کارت حقوقی"
    verbose_name_plural = "شماره‌های کارت حقوقی"

@admin.register(JuridicalProfile)
class JuridicalProfileAdmin(admin.ModelAdmin):
    form = JuridicalProfileForm
    list_display = (
        'id',
        'base_user__phone_number',
        'natural_profile__first_name',
        'natural_profile__last_name',
        'organization_name',
        'national_id',
        'registeration_number',
        'economical_code',
        'phone_number',
        'email',
        'status',
    )
    search_fields = (
        'base_user__phone_number',
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
    inlines = [JuridicalProfileDocumentInline, JuridicalCardNumberInline]  # افزودن اینلاین برای شماره‌های کارت

    def base_user__phone_number(self, obj):
        return obj.natural_profile.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

    def natural_profile__first_name(self, obj):
        return obj.natural_profile.first_name
    natural_profile__first_name.short_description = 'نام'

    def natural_profile__last_name(self, obj):
        return obj.natural_profile.last_name
    natural_profile__last_name.short_description = 'نام خانوادگی'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('natural_profile__base_user')
    
    
    
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