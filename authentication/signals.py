# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile

@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        # ایجاد پروفایل اولیه با مقادیر پیش‌فرض
        NaturalProfile.objects.create(
            base_user=instance,
            first_name='',
            last_name='',
            # هر فیلد دیگری که لازمه می‌تونی مقدار پیش‌فرض بدهی
        )
