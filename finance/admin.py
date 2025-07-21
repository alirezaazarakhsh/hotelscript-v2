from django.contrib import admin
from django.utils.html import format_html
from authentication.models import NaturalProfile
from finance.sms.sms import send_wallet_increase_sms
from .models import (
    Wallet,
    BankCard,
)

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
        super().save_model(request, obj, form, change)
        if change:  # فقط وقتی موجودی تغییر کرده
            old_balance = Wallet.objects.get(pk=obj.pk).balance - form.cleaned_data['balance']
            if old_balance != 0:  # اگه تغییر موجودی اتفاق افتاده
                amount_increased = form.cleaned_data['balance'] - old_balance
                send_wallet_increase_sms(obj.user, amount_increased)  # ارسال اس‌ام‌اس

@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'profile',
        'card_number',
        'sheba_number',
    )