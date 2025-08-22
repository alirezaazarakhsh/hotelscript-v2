# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel

@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        # گرفتن یا ساخت سطح میهمان
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')

        # ایجاد پروفایل تنها اگر وجود نداشته باشد
        profile, created_profile = NaturalProfile.objects.get_or_create(
            base_user=instance,
            defaults={
                'first_name': 'میهمان',
                'last_name': '.',
                'level': guest_level
            }
        )
        if created_profile:
            print(f"پروفایل جدید برای کاربر {instance.phone_number} ساخته شد.")
        else:
            print(f"پروفایل برای کاربر {instance.phone_number} قبلاً وجود داشته است.")

