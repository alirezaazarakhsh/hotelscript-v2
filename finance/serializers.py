from rest_framework import serializers
from .models import (
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
        fields = ['id', 'amount_1', 'amount_2', 'amount_3', 'amount_4']
        
        
class WalletTopUpSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        min_value=1_000_000,
        max_value=100_000_000,
        help_text="مبلغ افزایش کیف پول به ریال (بین 1,000,000 تا 100,000,000)"
    )