# bashgah_moshtarian/signals.py
import logging
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver

from authentication.models import BaseUser
from .models import CustomerClubPoint, RoomDiscountCode, ShoppingCenterDiscountCode
from .sms.sms import send_customer_club_sms, send_customer_club_deduct_sms, send_discount_sms

# ذخیره مقدار قبلی قبل از تغییر
@receiver(pre_save, sender=CustomerClubPoint)
def store_previous_points(sender, instance, **kwargs):
    if instance.pk:
        old = CustomerClubPoint.objects.get(pk=instance.pk)
        instance._previous_points = old.points
    else:
        instance._previous_points = 0

# بعد از ذخیره، ارسال SMS براساس تغییر امتیاز
@receiver(post_save, sender=CustomerClubPoint)
def send_club_points_sms(sender, instance, created, **kwargs):
    added_points = instance.points - getattr(instance, '_previous_points', 0)

    if added_points > 0:
        # افزایش امتیاز
        send_customer_club_sms(
            phone_number=instance.user.phone_number,
            user_name=instance.user.first_name,
            added_points=added_points,
            current_points=instance.points
        )
    elif added_points < 0:
        # کاهش امتیاز
        deducted_points = abs(added_points)
        send_customer_club_deduct_sms(
            phone_number=instance.user.phone_number,
            user_name=instance.user.first_name,
            deducted_points=deducted_points,
            current_points=instance.points
        )


# وقتی کد تخفیف اتاق ساخته یا تغییر داده شد
logger = logging.getLogger(__name__)

@receiver(m2m_changed, sender=RoomDiscountCode.users.through)
def send_room_discount_sms_signal(sender, instance, action, pk_set, **kwargs):
    """
    سیگنال برای ارسال پیامک تخفیف اتاق هنگام افزودن کاربر به کد تخفیف
    """
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = BaseUser.objects.get(pk=user_id)
                profile = getattr(user, 'natural_profile', None)
                full_name = (f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                             if profile else "کاربر")

                # اطمینان از اینکه full_name خالی نیست
                if not full_name:
                    full_name = "کاربر"
                    logger.warning(f"Empty full_name for user {user.phone_number}, using default 'کاربر'")

                # بررسی معتبر بودن phone_number
                if not user.phone_number:
                    logger.error(f"No phone number provided for user ID {user_id}")
                    continue

                # فراخوانی تابع ارسال پیامک
                result = send_discount_sms(
                    phone_number=user.phone_number,
                    user_name=full_name,
                    discount_code=instance.code,
                    location_name=str(instance.room),  # استفاده از نام اتاق
                )
                if not result:
                    logger.error(f"Failed to send SMS to {user.phone_number} for room discount code {instance.code}")

            except BaseUser.DoesNotExist:
                logger.warning(f"User with ID {user_id} does not exist")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in send_room_discount_sms_signal for user {user_id}: {str(e)}")
                continue

@receiver(m2m_changed, sender=ShoppingCenterDiscountCode.users.through)
def send_shopping_discount_sms_signal(sender, instance, action, pk_set, **kwargs):
    """
    سیگنال برای ارسال پیامک تخفیف مرکز خرید هنگام افزودن کاربر به کد تخفیف
    """
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = BaseUser.objects.get(pk=user_id)
                profile = getattr(user, 'natural_profile', None)
                full_name = (f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                             if profile else "کاربر")

                # اطمینان از اینکه full_name خالی نیست
                if not full_name:
                    full_name = "کاربر"
                    logger.warning(f"Empty full_name for user {user.phone_number}, using default 'کاربر'")

                # بررسی معتبر بودن phone_number
                if not user.phone_number:
                    logger.error(f"No phone number provided for user ID {user_id}")
                    continue

                # فراخوانی تابع ارسال پیامک
                result = send_discount_sms(
                    phone_number=user.phone_number,
                    user_name=full_name,
                    discount_code=instance.code,
                    location_name=instance.shopping_center_name,  # استفاده از نام مرکز خرید
                )
                if not result:
                    logger.error(f"Failed to send SMS to {user.phone_number} for shopping discount code {instance.code}")

            except BaseUser.DoesNotExist:
                logger.warning(f"User with ID {user_id} does not exist")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in send_shopping_discount_sms_signal for user {user_id}: {str(e)}")
                continue