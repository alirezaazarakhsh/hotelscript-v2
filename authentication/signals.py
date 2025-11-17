from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint
from bashgah_moshtarian.sms.sms import send_registration_gift_sms
from icons.models import IconShortcut
import logging
import threading
import time
import random

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BaseUser)
def create_user_related_records(sender, instance, created, **kwargs):
    if not created:
        return  # فقط کاربران جدید

    # ✅ جلوگیری از اجرا برای سوپر یوزر و ادمین‌ها
    if instance.is_superuser or instance.is_staff:
        logger.info(f"Skipping signal for admin user {instance.phone_number}")
        return

    logger.info(f"Running post_save signal for user {instance.phone_number}, created={created}")

    # ۱. آیکون پیش‌فرض
    default_icon, _ = IconShortcut.objects.get_or_create(
        order=1,
        defaults={
            'title_icon': 'آیکون پیش‌فرض',
            'svg_icon': 'media/svg_icons/verify.svg'
        }
    )

    # ۲. سطح میهمان
    guest_level, _ = UserLevel.objects.get_or_create(
        title='میهمان',
        defaults={
            'icon': default_icon,
            'color': '#000000',
        }
    )

    # ۳. پروفایل حقیقی
    profile, created_profile = NaturalProfile.objects.get_or_create(
        base_user=instance,
        defaults={
            'first_name': 'میهمان',
            'last_name': 'عزیز',
            'level': guest_level
        }
    )
    if created_profile:
        logger.info(f"Created new profile for user {instance.phone_number}")

    # ۴. امتیاز اولیه باشگاه مشتریان
    with transaction.atomic():
        customer_points, created_points = CustomerClubPoint.objects.select_for_update().get_or_create(
            user=instance,
            defaults={'points': 0, 'gift_sent': False}
        )

        if created_points:
            initial_points = 300
            customer_points.points += initial_points
            customer_points.gift_sent = True
            customer_points.save()
            logger.info(f"Added {initial_points} points for {instance.phone_number}")

            def send_gift_later():
                # تاخیر تصادفی بین 20 تا 30 ثانیه بعد از اس‌ام‌اس ورود
                delay = random.randint(20, 30)
                time.sleep(delay)
                send_registration_gift_sms(instance.phone_number, initial_points)

            threading.Thread(target=send_gift_later).start()
        else:
            logger.info(f"User {instance.phone_number} already has points: {customer_points.points}")
