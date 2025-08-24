from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint

@receiver(post_save, sender=BaseUser)
def create_user_related_records(sender, instance, created, **kwargs):
    if not created:
        return  # فقط برای کاربران جدید

    print(f"سیگنال post_save برای کاربر {instance.phone_number} اجرا شد. created={created}")

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
        print(f"پروفایل جدید برای کاربر {instance.phone_number} ساخته شد.")

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
            print(f"امتیاز {initial_points} برای {instance.phone_number} اضافه شد.")
        else:
            print(f"کاربر {instance.phone_number} قبلاً امتیاز دارد: {customer_points.points}")