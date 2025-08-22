# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile, UserLevel

@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        # ایجاد پروفایل اولیه با نام پیش‌فرض "میهمان"
        profile = NaturalProfile.objects.create(
            base_user=instance,
            first_name='میهمان',
            last_name='میهمان',
            # سایر فیلدها را می‌توان با مقدار پیش‌فرض تنظیم کرد
        )

        # تنظیم سطح پیش‌فرض کاربر به میهمان
        guest_level, _ = UserLevel.objects.get_or_create(name='میهمان')
        profile.level = guest_level
        profile.save()
