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
    AppGroup,
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
        'admin_avatar',
        'get_groups',
        'get_permissions_count',
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
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('base_user', 'first_name', 'last_name', 'image', 'signature')
        }),
        ('دسترسی‌های پیامکی', {
            'fields': ('sms_patterns',),
            'classes': ('collapse',),
        }),
        ('رمزها', {
            'fields': ('panel_password1', 'panel_password2', 'django_admin_password1', 'django_admin_password2'),
            'description': 'در صورت نیاز رمزها را تنظیم کنید. رمز جنگو باعث SuperUser شدن این کاربر می‌شود.',
        }),
    )

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
        groups = obj.base_user.groups.all()
        if groups:
            return format_html('<br>'.join([f'🔹 {g.name}' for g in groups]))
        return "—"
    get_groups.short_description = 'گروه‌های دسترسی'
    
    def get_permissions_count(self, obj):
        perms_count = obj.base_user.user_permissions.count()
        groups_count = obj.base_user.groups.count()
        return f"👤 {perms_count} | 👥 {groups_count}"
    get_permissions_count.short_description = 'دسترسی‌ها (مستقیم | گروهی)'

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
    
    


# SuperUser را از پنل ادمین مخفی می‌کنیم - فقط از طریق ترمینال قابل مدیریت است
# @admin.register(SuperUser)
# class SuperUserAdmin(admin.ModelAdmin):
#     list_display = ('id', 'base_user_info',)
#     search_fields = ('base_user__phone_number',)
#     ordering = ('-id',)

#     def base_user_info(self, obj):
#         profile_name = ""
#         if hasattr(obj.base_user, 'natural_profile') and obj.base_user.natural_profile:
#             profile_name = f"{obj.base_user.natural_profile.first_name or ''} {obj.base_user.natural_profile.last_name or ''}".strip()
#         return f"{obj.base_user.phone_number} ({profile_name or 'پروفایل موجود نیست'})"
#     base_user_info.short_description = 'موبایل و نام'
    
    

# گروه‌بندی اپلیکیشن‌ها
@admin.register(AppGroup)
class AppGroupAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'order', 'name', 'icon')
    list_editable = ('order',)
    search_fields = ('name', 'display_name')
    ordering = ('order', 'name')

# سفارشی‌سازی نمایش گروه‌ها برای نمایش تعداد ادمین‌های هر گروه
try:
    admin.site.unregister(Group)
except Exception:
    pass

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "admin_members_count")
    search_fields = ("name",)

    def admin_members_count(self, obj):
        return BaseUser.objects.filter(groups=obj, admin__isnull=False).count()
    admin_members_count.short_description = "تعداد ادمین‌های سایت"


@admin.register(BaseUser)
class BaseUserAdmin(admin.ModelAdmin):
    exclude = ('is_superuser', 'groups', 'user_permissions')
    
    list_display = (
        'id',
        'phone_number',
        'date_joined_jalali',
        'last_login_jalali',
        'user_type',
    )
    
    search_fields = ('phone_number',)
    ordering = ('-id',)
    
    # حذف filter_horizontal برای BaseUser - فقط برای ادمین‌ها نیاز است
    list_filter = ('is_superuser',)
    actions = ['make_admin']

    formfield_overrides = {
        jmodels.jDateTimeField: {'widget': AdminJalaliDateWidget},
    }

    readonly_fields = ('last_login_date', 'last_login_time', 'is_staff')
    
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