from rest_framework import serializers
from .models import (
    AdminCardSettings,
    DepositReceipt,
    Wallet,
    WalletPack,
    WithdrawalRequest,
    CardToCardInstruction,
)
from authentication.models import CardNumber, JuridicalCardNumber
from django.contrib.contenttypes.models import ContentType
import re

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
        min_value=1_000_000,      # حداقل 1 میلیون تومان
        max_value=100_000_000,    # حداکثر 100 میلیون تومان
        help_text="مبلغ افزایش کیف پول به تومان (بین 1,000,000 تا 100,000,000 تومان)"
    )





class AdminCardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminCardSettings
        fields = ['card_number', 'iban_number', 'account_holder_name']
        
        

class DepositReceiptSerializer(serializers.ModelSerializer):
    card_info = serializers.SerializerMethodField(read_only=True)
    profile_info = serializers.SerializerMethodField(read_only=True)
    card_number = serializers.CharField(read_only=True)
    card_iban = serializers.CharField(read_only=True)
    
    def get_card_info(self, obj):
        return obj.get_card_info()
    
    def get_profile_info(self, obj):
        return obj.get_profile_info()
    
    def validate_tracking_number(self, value):
        if not re.match(r'^\d{12}$', value):
            raise serializers.ValidationError("شماره پیگیری باید ۱۲ رقم باشد.")
        return value

    def validate_deposit_date_jalali(self, value):
        # اعتبارسنجی ساده فرمت YYYY/MM/DD
        if not re.match(r'^\d{4}/\d{2}/\d{2}$', value):
            raise serializers.ValidationError("فرمت تاریخ باید YYYY/MM/DD باشد.")
        return value
    
    def create(self, validated_data):
        # دریافت کاربر از request
        request = self.context.get('request')
        user = request.user
        
        # تنظیم user در instance
        validated_data['user'] = user
        
        # دریافت profile_type از validated_data
        profile_type = validated_data.get('profile_type')
        
        # تنظیم profile_content_type و profile_object_id بر اساس profile_type
        if profile_type == 'natural':
            try:
                natural_profile = user.natural_profile
                validated_data['profile_content_type'] = ContentType.objects.get_for_model(natural_profile)
                validated_data['profile_object_id'] = natural_profile.pk
            except Exception as e:
                raise serializers.ValidationError({"profile_type": "پروفایل حقیقی برای این کاربر یافت نشد."})
        elif profile_type == 'juridical':
            try:
                juridical_profile = user.natural_profile.juridical_profile
                validated_data['profile_content_type'] = ContentType.objects.get_for_model(juridical_profile)
                validated_data['profile_object_id'] = juridical_profile.pk
            except Exception as e:
                raise serializers.ValidationError({"profile_type": "پروفایل حقوقی برای این کاربر یافت نشد."})
        
        # دریافت card_object_id از validated_data
        # پذیرش دو حالت:
        #  - مقدار 1 یا 2 به عنوان اندیس کارتِ اول/دوم در پروفایل
        #  - یا یک PK واقعی از مدل CardNumber / JuridicalCardNumber که متعلق به پروفایل کاربر باشد
        card_index = validated_data.pop('card_object_id', None)
        if card_index is not None:
            # کوشش برای تبدیل به عدد
            try:
                card_index_int = int(card_index)
            except (TypeError, ValueError):
                raise serializers.ValidationError({"card_object_id": "card_object_id باید عددی باشد."})

            if profile_type == 'natural':
                cards_qs = CardNumber.objects.filter(profile=user.natural_profile).order_by('id')

                # اگر کاربر مقدار 1 یا 2 فرستاده، آن را به عنوان اندیس تفسیر کن
                if card_index_int in (1, 2):
                    idx = card_index_int - 1
                    if cards_qs.count() > idx:
                        card = cards_qs[idx]
                    else:
                        raise serializers.ValidationError({"card_object_id": f"کارت شماره {card_index_int} برای این پروفایل یافت نشد."})
                else:
                    # تلاش برای یافتن کارت با PK داده‌شده و متعلق به پروفایل
                    try:
                        card = cards_qs.get(pk=card_index_int)
                    except CardNumber.DoesNotExist:
                        raise serializers.ValidationError({"card_object_id": f"کارت با شناسه {card_index_int} برای این پروفایل یافت نشد."})

                validated_data['card_content_type'] = ContentType.objects.get_for_model(card)
                validated_data['card_object_id'] = card.pk

            elif profile_type == 'juridical':
                cards_qs = JuridicalCardNumber.objects.filter(profile=user.natural_profile.juridical_profile).order_by('id')

                if card_index_int in (1, 2):
                    idx = card_index_int - 1
                    if cards_qs.count() > idx:
                        card = cards_qs[idx]
                    else:
                        raise serializers.ValidationError({"card_object_id": f"کارت شماره {card_index_int} برای این پروفایل یافت نشد."})
                else:
                    try:
                        card = cards_qs.get(pk=card_index_int)
                    except JuridicalCardNumber.DoesNotExist:
                        raise serializers.ValidationError({"card_object_id": f"کارت با شناسه {card_index_int} برای این پروفایل یافت نشد."})

                validated_data['card_content_type'] = ContentType.objects.get_for_model(card)
                validated_data['card_object_id'] = card.pk
        
        return super().create(validated_data)

    class Meta:
        model = DepositReceipt
        fields = [
            'id',
            'profile_type',
            'card_object_id',
            'depositor_name',
            'tracking_number',
            'amount',
            'deposit_date_jalali',
            'receipt_image',
            'is_approved',
            'card_number',
            'card_iban',
            'card_info',
            'profile_info',
        ]
        read_only_fields = ('is_approved', 'card_info', 'profile_info', 'card_number', 'card_iban')


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    card_info = serializers.SerializerMethodField(read_only=True)
    profile_info = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    def get_card_info(self, obj):
        return obj.get_card_info()
    
    def get_profile_info(self, obj):
        return obj.get_profile_info()
    
    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        amount = data.get('amount')
        
        # بررسی موجودی کیف پول
        try:
            wallet = user.wallet
            if wallet.balance < int(amount):
                raise serializers.ValidationError({
                    'amount': f'موجودی کیف پول شما کافی نیست. موجودی فعلی: {wallet.balance:,} تومان'
                })
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({'amount': 'کیف پول برای این کاربر یافت نشد.'})
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        validated_data['user'] = user
        profile_type = validated_data.get('profile_type')
        
        if profile_type == 'natural':
            try:
                natural_profile = user.natural_profile
                validated_data['profile_content_type'] = ContentType.objects.get_for_model(natural_profile)
                validated_data['profile_object_id'] = natural_profile.pk
            except Exception as e:
                raise serializers.ValidationError({'profile_type': 'پروفایل حقیقی برای این کاربر یافت نشد.'})
        elif profile_type == 'juridical':
            try:
                juridical_profile = user.natural_profile.juridical_profile
                validated_data['profile_content_type'] = ContentType.objects.get_for_model(juridical_profile)
                validated_data['profile_object_id'] = juridical_profile.pk
            except Exception as e:
                raise serializers.ValidationError({'profile_type': 'پروفایل حقوقی برای این کاربر یافت نشد.'})
        
        card_index = validated_data.pop('card_object_id', None)
        if card_index is not None:
            # کوشش برای تبدیل به عدد
            try:
                card_index_int = int(card_index)
            except (TypeError, ValueError):
                raise serializers.ValidationError({'card_object_id': 'card_object_id باید عددی باشد.'})

            if profile_type == 'natural':
                cards_qs = CardNumber.objects.filter(profile=user.natural_profile).order_by('id')

                if card_index_int in (1, 2):
                    idx = card_index_int - 1
                    if cards_qs.count() > idx:
                        card = cards_qs[idx]
                    else:
                        raise serializers.ValidationError({'card_object_id': f'کارت شماره {card_index_int} برای این پروفایل یافت نشد.'})
                else:
                    try:
                        card = cards_qs.get(pk=card_index_int)
                    except CardNumber.DoesNotExist:
                        raise serializers.ValidationError({'card_object_id': f'کارت با شناسه {card_index_int} برای این پروفایل یافت نشد.'})

                validated_data['card_content_type'] = ContentType.objects.get_for_model(card)
                validated_data['card_object_id'] = card.pk

            elif profile_type == 'juridical':
                cards_qs = JuridicalCardNumber.objects.filter(profile=user.natural_profile.juridical_profile).order_by('id')

                if card_index_int in (1, 2):
                    idx = card_index_int - 1
                    if cards_qs.count() > idx:
                        card = cards_qs[idx]
                    else:
                        raise serializers.ValidationError({'card_object_id': f'کارت شماره {card_index_int} برای این پروفایل یافت نشد.'})
                else:
                    try:
                        card = cards_qs.get(pk=card_index_int)
                    except JuridicalCardNumber.DoesNotExist:
                        raise serializers.ValidationError({'card_object_id': f'کارت با شناسه {card_index_int} برای این پروفایل یافت نشد.'})

                validated_data['card_content_type'] = ContentType.objects.get_for_model(card)
                validated_data['card_object_id'] = card.pk
        
        return super().create(validated_data)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id',
            'profile_type',
            'card_object_id',
            'amount',
            'card_number',
            'card_iban',
            'card_holder_name',
            'status',
            'status_display',
            'admin_note',
            'created_at',
            'updated_at',
            'card_info',
            'profile_info',
        ]
        read_only_fields = (
            'status', 
            'admin_note', 
            'created_at', 
            'updated_at', 
            'card_info', 
            'profile_info',
            'card_number',
            'card_iban',
            'card_holder_name',
            'status_display',
        )


class CardToCardInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardToCardInstruction
        fields = ['text']
        read_only_fields = ['text']
