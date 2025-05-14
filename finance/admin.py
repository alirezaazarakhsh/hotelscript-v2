from django.contrib import admin
from .models import (
    Wallet,
)

# Register your models here.
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'balance',
    )
