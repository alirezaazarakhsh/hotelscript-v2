from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import RoomDiscountCode, ShoppingCenterDiscountCode
from .sms import send_discount_code_sms
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=RoomDiscountCode)
def send_room_discount_code_sms(sender, instance, created, **kwargs):
    """
    سیگنال برای ارسال پیامک هنگام ایجاد کد تخفیف اتاق.
    """
    if created:
        logger.info(f"New RoomDiscountCode created: {instance.code}. Triggering SMS.")
        success = send_discount_code_sms(instance, pattern_section='discountcode')
        if success:
            logger.info(f"SMS sent successfully for RoomDiscountCode: {instance.code}")
        else:
            logger.error(f"Failed to send SMS for RoomDiscountCode: {instance.code}")

@receiver(post_save, sender=ShoppingCenterDiscountCode)
def send_shopping_center_discount_code_sms(sender, instance, created, **kwargs):
    """
    سیگنال برای ارسال پیامک هنگام ایجاد کد تخفیف مرکز خرید.
    """
    if created:
        logger.info(f"New ShoppingCenterDiscountCode created: {instance.code}. Triggering SMS.")
        success = send_discount_code_sms(instance, pattern_section='discountcode')
        if success:
            logger.info(f"SMS sent successfully for ShoppingCenterDiscountCode: {instance.code}")
        else:
            logger.error(f"Failed to send SMS for ShoppingCenterDiscountCode: {instance.code}")
