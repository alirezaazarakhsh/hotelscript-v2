# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel


@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        # پیدا کردن سطح کاربری "میهمان"
        guest_level = UserLevel.objects.filter(title='میهمان').first()

        # ایجاد پروفایل اولیه با مقادیر پیش‌فرض
        NaturalProfile.objects.create(
            base_user=instance,
            first_name='میهمان',
            last_name='.',
            level=guest_level  # اگر "میهمان" تعریف شده باشه، اینجا ست میشه
        )
