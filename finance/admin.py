from django.contrib import admin
from .models import (
    Wallet,
    BankCard,
)

# Register your models here.
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'balance',
    )

@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'profile',
        'card_number',
        'sheba_number',
    )
