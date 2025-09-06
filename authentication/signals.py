from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint
from bashgah_moshtarian.sms.sms import send_registration_gift_sms
import logging
import threading
import time

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BaseUser)
def create_user_related_records(sender, instance, created, **kwargs):
    if not created:
        return  # فقط کاربران جدید

    logger.info(f"Running post_save signal for user {instance.phone_number}, created={created}")

    # اگر سوپر یوزر است، هیچ پروفایل یا رکورد مرتبط نساز
    if instance.is_superuser:
        logger.info(f"User {instance.phone_number} is superuser, skipping profile creation and points setup.")
        return

    # ۱. ساخت سطح میهمان فقط برای کاربران عادی
    # اگر لازم است می‌توانید یک آیکون پیش‌فرض برای این سطح اضافه کنید
    try:
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')
    except Exception as e:
        logger.error(f"Cannot create guest UserLevel for user {instance.phone_number}: {e}")
        guest_level = None

    # ۲. ساخت پروفایل حقیقی
    profile_defaults = {
        'first_name': 'میهمان',
        'last_name': 'عزیز',
        'level': guest_level
    } if guest_level else {
        'first_name': 'میهمان',
        'last_name': 'عزیز',
    }

    profile, created_profile = NaturalProfile.objects.get_or_create(
        base_user=instance,
        defaults=profile_defaults
    )
    if created_profile:
        logger.info(f"Created new profile for user {instance.phone_number}")

    # ۳. ایجاد رکورد باشگاه مشتریان و اضافه کردن امتیاز اولیه
    with transaction.atomic():
        customer_points, created_points = CustomerClubPoint.objects.select_for_update().get_or_create(
            user=instance,
            defaults={'points': 0}
        )

        if created_points:
            initial_points = 300
            customer_points.points += initial_points
            customer_points.save()
            logger.info(f"Added {initial_points} points for {instance.phone_number}")

            # ارسال پیامک هدیه ثبت‌نام بعد از ۵ ثانیه با Threading
            def send_gift_later():
                time.sleep(5)
                send_registration_gift_sms(instance.phone_number, initial_points)

            threading.Thread(target=send_gift_later).start()
        else:
            logger.info(f"User {instance.phone_number} already has points: {customer_points.points}")
