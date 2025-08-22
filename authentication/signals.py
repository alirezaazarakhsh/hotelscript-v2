# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel  # فرض بر این است که UserLevel در app config است

@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        # ایجاد پروفایل اولیه با مقادیر پیش‌فرض
        NaturalProfile.objects.create(
            base_user=instance,
            first_name='میهمان',
            last_name='کاربر',
        )

        # ست کردن سطح کاربری پیش‌فرض
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')
        instance.user_level = guest_level
        instance.save()
