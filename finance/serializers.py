from rest_framework import serializers
from .models import (
    AdminCardSettings,
    DepositReceipt,
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
        
        

class DepositReceiptSerializer(serializers.ModelSerializer):
    
    def validate_tracking_number(self, value):
        if not re.match(r'^\d{12}$', value):
            raise serializers.ValidationError("شماره پیگیری باید ۱۲ رقم باشد.")
        return value

    def validate_deposit_date_jalali(self, value):
        # اعتبارسنجی ساده فرمت YYYY/MM/DD
        if not re.match(r'^\d{4}/\d{2}/\d{2}$', value):
            raise serializers.ValidationError("فرمت تاریخ باید YYYY/MM/DD باشد.")
        return value

    class Meta:
        model = DepositReceipt
        fields = [
            'id',
            'depositor_name',
            'tracking_number',
            'amount',
            'deposit_date_jalali',
            'receipt_image',
            'is_approved',
        ]
        read_only_fields = ('is_approved',)  # تایید توسط ادمین انجام می‌شود