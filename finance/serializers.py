from rest_framework import serializers
from .models import (
    AdminCardSettings,
    Wallet,
    WalletPack,
)

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance']
        
        
class WalletPackSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletPack
        fields = ['amount_1', 'amount_2', 'amount_3', 'amount_4']
        
        
class WalletTopUpSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        min_value=100_000,   # 100 هزار تومان یعنی 1 میلیون ریال
        max_value=10_000_000,  # 10 میلیون تومان یعنی 100 میلیون ریال
        help_text="مبلغ افزایش کیف پول به تومان (بین 100,000 تا 10,000,000 تومان)"
    )




class AdminCardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminCardSettings
        fields = ['card_number', 'iban_number', 'account_holder_name']