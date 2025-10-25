import requests
import json
from django.conf import settings
from .models import ZarinpalGateway, IranianGateway, PaymentGatewayPreference
import logging

logger = logging.getLogger(__name__)

class PaymentGatewayService:
    # آدرس‌های ایران درگاه (فقط محیط تولید)
    IRANIAN_PRODUCTION_PAYMENT_URL = "https://dargaah.ir/payment"
    IRANIAN_PRODUCTION_VERIFICATION_URL = "https://dargaah.ir/verification"
    IRANIAN_PAYMENT_URL = "https://dargaah.ir/ird/startpay/{authority}"

    # آدرس‌های زرین‌پال (محیط تولید)
    ZARINPAL_PAYMENT_URL = "https://www.zarinpal.com/pg/StartPay/{authority}"
    ZARINPAL_VERIFICATION_URL = "https://www.zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
    ZARINPAL_PAYMENT_GATEWAY_URL = "https://www.zarinpal.com/pg/StartPay/{authority}"

    @staticmethod
    def get_active_gateway():
        preference = PaymentGatewayPreference.objects.first()
        return preference.active_gateway if preference else 'zarinpal'  # پیش‌فرض زرین‌پال

    @staticmethod
    def get_merchant_id():
        active_gateway = PaymentGatewayService.get_active_gateway()
        if active_gateway == 'iraniangateway':
            gateway = IranianGateway.objects.first()
            return gateway.merchant_code if gateway else ""
        elif active_gateway == 'zarinpal':
            gateway = ZarinpalGateway.objects.first()
            return gateway.merchant_code if gateway else ""
        return ""

    @staticmethod
    def create_transaction(amount, callback_url, order_id, mobile=None, description=None):
        active_gateway = PaymentGatewayService.get_active_gateway()
        merchant_id = PaymentGatewayService.get_merchant_id()
        if not merchant_id:
            raise ValueError("مرچنت کد برای درگاه فعال تنظیم نشده است.")

        if active_gateway == 'iraniangateway':
            data = {
                "merchantID": merchant_id,
                "amount": amount,
                "callbackURL": callback_url,
                "orderId": order_id,
                "mobile": mobile,
                "description": description,
            }
            payment_url_base = PaymentGatewayService.IRANIAN_PAYMENT_URL
            request_url = PaymentGatewayService.IRANIAN_PRODUCTION_PAYMENT_URL
        elif active_gateway == 'zarinpal':
            data = {
                "merchant_id": merchant_id,
                "amount": amount,
                "description": description,
                "callback_url": callback_url,
                "metadata": {"mobile": mobile, "order_id": order_id}
            }
            payment_url_base = PaymentGatewayService.ZARINPAL_PAYMENT_URL
            request_url = PaymentGatewayService.ZARINPAL_PAYMENT_GATEWAY_URL
        else:
            raise ValueError("درگاه فعال پشتیبانی نمی‌شود.")

        # تنظیم هدر Referer با دامنه فعلی
        referer_url = getattr(settings, 'SITE_URL', 'https://cps.safarnameh24.com')
        headers = {
            'Content-Type': 'application/json',
            'Referer': referer_url
        }
        response = requests.post(
            request_url,
            data=json.dumps(data),
            headers=headers
        )

        response_data = response.json()
        logger.info(f"Response from {active_gateway} (create): {response.text}")
        if active_gateway == 'iraniangateway' and response_data.get("status") == 200:
            return response_data.get("authority")
        elif active_gateway == 'zarinpal' and response_data.get("data") and response_data["data"].get("code") == 100:
            return response_data["data"].get("authority")
        else:
            raise ValueError(f"خطا در ایجاد تراکنش: {response_data.get('message', response_data.get('errors', 'خطای ناشناخته'))}")

    @staticmethod
    def verify_transaction(authority, amount, order_id):
        active_gateway = PaymentGatewayService.get_active_gateway()
        merchant_id = PaymentGatewayService.get_merchant_id()
        if not merchant_id:
            raise ValueError("مرچنت کد برای درگاه فعال تنظیم نشده است.")

        if active_gateway == 'iraniangateway':
            data = {
                "merchantID": merchant_id,
                "authority": authority,
                "amount": amount,
                "orderId": order_id,
            }
            verification_url = PaymentGatewayService.IRANIAN_PRODUCTION_VERIFICATION_URL
        elif active_gateway == 'zarinpal':
            data = {
                "merchant_id": merchant_id,
                "authority": authority,
                "amount": amount
            }
            verification_url = PaymentGatewayService.ZARINPAL_VERIFICATION_URL
        else:
            raise ValueError("درگاه فعال پشتیبانی نمی‌شود.")

        headers = {
            'Content-Type': 'application/json',
            'Referer': getattr(settings, 'SITE_URL', 'https://cps.safarnameh24.com')
        }
        response = requests.post(
            verification_url,
            data=json.dumps(data),
            headers=headers
        )

        response_data = response.json()
        logger.info(f"Response from {active_gateway} (verify): {response.text}")
        if active_gateway == 'iraniangateway' and response_data.get("status") == 100:
            return response_data.get("refId")
        elif active_gateway == 'zarinpal' and response_data.get("data") and response_data["data"].get("code") == 100:
            return response_data["data"].get("ref_id")
        else:
            raise ValueError(f"خطا در تأیید تراکنش: {response_data.get('message', response_data.get('errors', 'خطای ناشناخته'))}")

    @staticmethod
    def get_payment_url(authority):
        active_gateway = PaymentGatewayService.get_active_gateway()
        if active_gateway == 'iraniangateway':
            return PaymentGatewayService.IRANIAN_PAYMENT_URL.format(authority=authority)
        elif active_gateway == 'zarinpal':
            return PaymentGatewayService.ZARINPAL_PAYMENT_URL.format(authority=authority)
        raise ValueError("درگاه فعال پشتیبانی نمی‌شود.")