import requests
import json
from django.conf import settings
from .models import IranianGateway, PaymentGatewayPreference

class PaymentGatewayService:
    # آدرس‌های ایران درگاه
    IRANIAN_SANDBOX_PAYMENT_URL = "https://dargaah.ir/sandbox/payment"
    IRANIAN_SANDBOX_VERIFICATION_URL = "https://dargaah.ir/sandbox/verification"
    IRANIAN_PRODUCTION_PAYMENT_URL = "https://dargaah.ir/payment"
    IRANIAN_PRODUCTION_VERIFICATION_URL = "https://dargaah.ir/verification"
    IRANIAN_PAYMENT_URL = "https://dargaah.ir/sandbox/ird/startpay/{authority}" if settings.DEBUG else "https://dargaah.ir/ird/startpay/{authority}"

    @staticmethod
    def get_active_gateway():
        preference = PaymentGatewayPreference.objects.first()
        return preference.active_gateway if preference else 'iraniangateway'  # پیش‌فرض ایران درگاه

    @staticmethod
    def get_merchant_id():
        if PaymentGatewayService.get_active_gateway() == 'iraniangateway':
            gateway = IranianGateway.objects.first()
            return "TEST" if settings.DEBUG else (gateway.merchant_code if gateway else "")
        return ""

    @staticmethod
    def create_transaction(amount, callback_url, order_id, card_number="1234123412341234", mobile=None, description=None):
        if PaymentGatewayService.get_active_gateway() != 'iraniangateway':
            raise ValueError("درگاه فعال ایران درگاه نیست.")

        merchant_id = PaymentGatewayService.get_merchant_id()
        if not merchant_id:
            raise ValueError("مرچنت کد برای ایران درگاه تنظیم نشده است.")

        data = {
            "merchantID": merchant_id,
            "amount": amount,  # به ریال، بدون اعشار
            "callbackURL": callback_url,
            "orderId": order_id,
            "cardNumber": card_number,  # برای سندباکس
            "mobile": mobile,
            "description": description,
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            PaymentGatewayService.IRANIAN_SANDBOX_PAYMENT_URL if settings.DEBUG else PaymentGatewayService.IRANIAN_PRODUCTION_PAYMENT_URL,
            data=json.dumps(data),
            headers=headers
        )

        response_data = response.json()
        if response_data.get("status") == 200:
            return response_data.get("authority")
        else:
            raise ValueError(f"خطا در ایجاد تراکنش: {response_data.get('message')}")

    @staticmethod
    def verify_transaction(authority, amount, order_id):
        if PaymentGatewayService.get_active_gateway() != 'iraniangateway':
            raise ValueError("درگاه فعال ایران درگاه نیست.")

        merchant_id = PaymentGatewayService.get_merchant_id()
        if not merchant_id:
            raise ValueError("مرچنت کد برای ایران درگاه تنظیم نشده است.")

        data = {
            "merchantID": merchant_id,
            "authority": authority,
            "amount": amount,
            "orderId": order_id,
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            PaymentGatewayService.IRANIAN_SANDBOX_VERIFICATION_URL if settings.DEBUG else PaymentGatewayService.IRANIAN_PRODUCTION_VERIFICATION_URL,
            data=json.dumps(data),
            headers=headers
        )

        response_data = response.json()
        if response_data.get("status") == 100:
            return response_data.get("refId")
        else:
            raise ValueError(f"خطا در تأیید تراکنش: {response_data.get('message')}")

    @staticmethod
    def get_payment_url(authority):
        if PaymentGatewayService.get_active_gateway() != 'iraniangateway':
            raise ValueError("درگاه فعال ایران درگاه نیست.")
        return PaymentGatewayService.IRANIAN_PAYMENT_URL.format(authority=authority)
    