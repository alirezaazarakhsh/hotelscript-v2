from django.contrib import admin
from django.utils.html import format_html
from authentication.models import NaturalProfile
from finance.sms.sms import send_wallet_increase_sms
from .models import (
    Wallet,
    BankCard,
    WalletPack,
)

from django.contrib import admin
from .models import WalletPack

from django.contrib import admin
from .models import WalletPack



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

    def save_model(self, request, obj, form, change):
        if change:  # فقط برای به‌روزرسانی
            old_wallet = Wallet.objects.get(pk=obj.pk)  # بازیابی موجودی قبلی
            old_balance = old_wallet.balance
            super().save_model(request, obj, form, change)  # ذخیره مدل جدید
            if old_balance != form.cleaned_data['balance']:  # بررسی تغییر موجودی
                amount_increased = form.cleaned_data['balance'] - old_balance
                send_wallet_increase_sms(obj.user, amount_increased)  # ارسال پیامک
        else:
            super().save_model(request, obj, form, change)  # برای ایجاد مدل جدید

@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'profile',
        'card_number',
        'sheba_number',
    )