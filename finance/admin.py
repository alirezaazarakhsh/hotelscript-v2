from django.contrib import admin
from django.utils.html import format_html
from authentication.models import NaturalProfile
from finance.sms.sms import send_wallet_increase_sms
from .models import (
    AdminCardSettings,
    DepositReceipt,
    Wallet,
    WalletPack,
)


@admin.register(WalletPack)
class WalletPackAdmin(admin.ModelAdmin):
    list_display = ('id', 'formatted_amount_1', 'formatted_amount_2', 'formatted_amount_3', 'formatted_amount_4')
    search_fields = ('amount_1', 'amount_2', 'amount_3', 'amount_4')

    def has_add_permission(self, request):
        if WalletPack.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return WalletPack.objects.exists()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)

    def formatted_amount_1(self, obj):
        return format_html(f'{obj.amount_1:,.0f} تومان')
    formatted_amount_1.short_description = 'مبلغ پکیج یک'

    def formatted_amount_2(self, obj):
        return format_html(f'{obj.amount_2:,.0f} تومان')
    formatted_amount_2.short_description = 'مبلغ پکیج دوم'

    def formatted_amount_3(self, obj):
        return format_html(f'{obj.amount_3:,.0f} تومان')
    formatted_amount_3.short_description = 'مبلغ پکیج سوم'

    def formatted_amount_4(self, obj):
        return format_html(f'{obj.amount_4:,.0f} تومان')
    formatted_amount_4.short_description = 'مبلغ پکیج چهارم'

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ['amount_1', 'amount_2', 'amount_3', 'amount_4']:
            field.widget.attrs['step'] = '0.01'  # اجازه ورود اعشار
            field.localize = True  # برای فرمت‌دهی محلی
            # سفارشی‌سازی نمایش (هرچند این بخش به تنهایی کافی نیست، نیاز به جاوااسکریپت دارد)
        return field    
    


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_user_display',
        'balance',
    )
    search_fields = (
        'user__natural_profile__first_name',
        'user__natural_profile__last_name',
        'user__phone_number',
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('get_user_display',)

    fieldsets = (
        (None, {
            'fields': (
                'user',
                'balance',
                'get_user_display',
            )
        }),
    )

    def get_user_display(self, obj):
        try:
            natural_profile = obj.user.natural_profile
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<span>{} {}</span>'
                '<span style="margin-left:8px;">({})</span>'
                '</div>',
                natural_profile.first_name or '',
                natural_profile.last_name or '',
                obj.user.phone_number
            )
        except NaturalProfile.DoesNotExist:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<span>{} (بدون پروفایل)</span>'
                '</div>',
                obj.user.phone_number
            )
    get_user_display.short_description = "مشخصات کاربر"
    
    
    

@admin.register(AdminCardSettings)
class AdminCardSettingsAdmin(admin.ModelAdmin):
    list_display = ('account_holder_name', 'card_number', 'iban_number')
    search_fields = ('account_holder_name', 'card_number', 'iban_number')

    def has_add_permission(self, request):
        # اگر رکوردی وجود داشت، اجازه اضافه کردن رکورد جدید نده
        if AdminCardSettings.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # فقط وقتی رکورد هست، اجازه حذف بده
        return AdminCardSettings.objects.exists()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # دکمه "Save and add another" را غیر فعال کن
        extra_context = extra_context or {}
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    
    
@admin.register(DepositReceipt)
class DepositReceiptAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'depositor_name',
        'tracking_number',
        'amount',
        'deposit_date_jalali',
        'profile_type',
        'is_approved',
        'receipt_image_preview',
    )
    list_filter = ('is_approved', 'profile_type')
    search_fields = ('tracking_number', 'depositor_name', 'user__phone_number')
    readonly_fields = ('receipt_image_preview', 'deposit_date_jalali', 'user', 'profile_info_display', 'card_info_display', 'card_snapshot_display')

    actions = ['approve_receipts']
    
    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user', 'profile_type', 'profile_info_display', 'card_snapshot_display')
        }),
        ('اطلاعات واریز', {
            'fields': ('depositor_name', 'tracking_number', 'amount', 'deposit_date_jalali', 'receipt_image', 'receipt_image_preview')
        }),
        ('وضعیت', {
            'fields': ('is_approved',)
        }),
    )

    def profile_info_display(self, obj):
        """نمایش اطلاعات پروفایل"""
        info = obj.get_profile_info()
        if info:
            if obj.profile_type == 'natural':
                return format_html(
                    "<b>نوع:</b> {} <br><b>نام:</b> {} {} <br><b>کد ملی:</b> {}",
                    info.get('type', '-'),
                    info.get('first_name', '-'),
                    info.get('last_name', '-'),
                    info.get('national_code', '-')
                )
            elif obj.profile_type == 'juridical':
                return format_html(
                    "<b>نوع:</b> {} <br><b>نام سازمان:</b> {} <br><b>شناسه ملی:</b> {}",
                    info.get('type', '-'),
                    info.get('organization_name', '-'),
                    info.get('national_id', '-')
                )
        return "-"
    profile_info_display.short_description = "اطلاعات پروفایل"
    
    def card_info_display(self, obj):
        """نمایش اطلاعات کارت بانکی"""
        info = obj.get_card_info()
        if info:
            return format_html(
                "<b>شماره کارت:</b> {} <br><b>شبا:</b> {} <br><b>صاحب حساب:</b> {}",
                info.get('card_number', '-'),
                info.get('iban', '-'),
                info.get('account_holder', '-')
            )
        return "-"
    card_info_display.short_description = "اطلاعات کارت"

    def card_snapshot_display(self, obj):
        return format_html(
            "<b>شماره کارت ذخیره‌شده:</b> {}<br><b>شبا ذخیره‌شده:</b> {}",
            obj.card_number or '-', obj.card_iban or '-'
        )
    card_snapshot_display.short_description = 'Snapshot کارت'

    def receipt_image_preview(self, obj):
        if obj.receipt_image:
            return format_html('<img src="{}" style="height: 80px; border-radius: 4px;" />', obj.receipt_image.url)
        return "-"
    receipt_image_preview.short_description = "پیش نمایش فیش"

    def approve_receipts(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} فیش واریزی تایید شد و مبلغ به کیف پول کاربران اضافه شد.")
    approve_receipts.short_description = "تایید فیش‌های انتخاب شده"