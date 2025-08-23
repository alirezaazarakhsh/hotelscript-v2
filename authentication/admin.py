from django.contrib import admin
from django import forms
from django_jalali.db import models as jmodels
from jalali_date.widgets import AdminJalaliDateWidget  
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

# به‌روزرسانی AdminAdmin برای اضافه کردن اینلاین
@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'id',
        'base_user__phone_number',
        'first_name',
        'last_name',
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
    )
    ordering = (
        '-id',
    )
    # inlines = [AdminSMSPatternInline]

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'



# بقیه کدهای admin.py بدون تغییر
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

    # نمایش تاریخ ثبت‌نام به صورت جلالی
    def date_joined_jalali(self, obj):
        if obj.date_joined:
            return jdatetime.datetime.fromgregorian(datetime=obj.date_joined).strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    date_joined_jalali.short_description = 'تاریخ ثبت‌نام'

    # نمایش آخرین ورود به صورت جلالی
    def last_login_jalali(self, obj):
        if obj.last_login:
            return jdatetime.datetime.fromgregorian(datetime=obj.last_login).strftime('%Y/%m/%d %H:%M:%S')
        return "-"
    last_login_jalali.short_description = 'آخرین ورود'

    # تاریخ آخرین ورود فقط تاریخ
    def last_login_date(self, obj):
        if obj.last_login:
            return jdatetime.datetime.fromgregorian(datetime=obj.last_login).strftime('%Y/%m/%d')
        return "-"
    last_login_date.short_description = 'تاریخ آخرین ورود'

    # زمان آخرین ورود فقط ساعت
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