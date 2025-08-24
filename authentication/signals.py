from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BaseUser)
def create_user_related_records(sender, instance, created, **kwargs):
    if not created:
        return  # فقط برای کاربران جدید

    logger.info(f"Running post_save signal for user {instance.phone_number}, created={created}")

    # ۱. ساخت سطح میهمان
    guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')

    # ۲. ساخت پروفایل حقیقی
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
        else:
            logger.info(f"User {instance.phone_number} already has points: {customer_points.points}")