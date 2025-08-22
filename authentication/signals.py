from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel

@receiver(post_save, sender=BaseUser)
def create_natural_profile(sender, instance, created, **kwargs):
    if created:
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')
        # پروفایل حقیقی بساز اگر هنوز ساخته نشده
        NaturalProfile.objects.get_or_create(
            base_user=instance,
            defaults={
                'first_name': 'میهمان',
                'last_name': '.',
                'level': guest_level
            }
        )
