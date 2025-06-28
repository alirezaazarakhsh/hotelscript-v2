from rest_framework import serializers
from .models import (
    BankCard,
)

class BankCardSerializer(serializers.ModelSerializer):
    profile_type = serializers.CharField(
        write_only=True,
        help_text='Profile type (options: [natural, juridical])'
    )

    class Meta:
        model = BankCard
        fields = (
            'card_number',
            'sheba_number',
            'profile_type',
        )


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance']