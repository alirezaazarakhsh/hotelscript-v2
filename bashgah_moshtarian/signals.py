# bashgah_moshtarian/signals.py
import logging
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from threading import local
from authentication.models import BaseUser
from .models import CustomerClubPoint, RoomDiscountCode, ShoppingCenterDiscountCode
from .sms.sms import send_customer_club_sms, send_customer_club_deduct_sms, send_discount_sms

logger = logging.getLogger(__name__)

# متغیر محلی برای کنترل ارسال SMS
_thread_locals = local()

def set_skip_sms(value):
    setattr(_thread_locals, 'skip_sms', value)

def get_skip_sms():
    return getattr(_thread_locals, 'skip_sms', False)

@receiver(pre_save, sender=CustomerClubPoint)
def store_previous_points(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = CustomerClubPoint.objects.get(pk=instance.pk)
            instance._previous_points = old.points
        except CustomerClubPoint.DoesNotExist:
            instance._previous_points = 0
    else:
        instance._previous_points = 0

@receiver(post_save, sender=CustomerClubPoint)
def send_club_points_sms(sender, instance, created, **kwargs):
    if get_skip_sms():
        logger.info(f"ارسال SMS برای کاربر {instance.user.phone_number} نادیده گرفته شد.")
        return

    added_points = instance.points - getattr(instance, '_previous_points', 0)
    if added_points != 0:
        logger.info(f"تغییر امتیاز برای کاربر {instance.user.phone_number}: {added_points} (امتیاز فعلی: {instance.points})")
        user_name = instance.user.first_name or instance.user.phone_number
        if added_points > 0:
            send_customer_club_sms(
                phone_number=instance.user.phone_number,
                user_name=user_name,
                added_points=added_points,
                current_points=instance.points
            )
        else:
            send_customer_club_deduct_sms(
                phone_number=instance.user.phone_number,
                user_name=user_name,
                deducted_points=abs(added_points),
                current_points=instance.points
            )
    else:
        logger.info(f"هیچ تغییری در امتیاز برای کاربر {instance.user.phone_number} رخ نداده است.")

@receiver(post_save, sender=RoomDiscountCode)
@receiver(post_save, sender=ShoppingCenterDiscountCode)
def send_discount_sms_on_discount_code_save(sender, instance, created, **kwargs):
    if created or instance.users.exists():
        logger.info(f"ارسال SMS تخفیف برای کد {instance.code} به کاربران.")
        send_discount_sms(instance, send_to_all=True)