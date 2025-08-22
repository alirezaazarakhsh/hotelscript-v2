from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from authentication.models import BaseUser
from config.models import UserLevel
from .models import NaturalProfile

@receiver(user_logged_in)
def create_profile_on_login(sender, request, user, **kwargs):
    """
    وقتی کاربر لاگین می‌کند، اگر پروفایل حقیقی ندارد، بساز و سطحش را میهمان کن.
    """
    if not hasattr(user, 'natural_profile'):
        default_level = UserLevel.objects.filter(name='میهمان').first()
        NaturalProfile.objects.create(user=user, level=default_level)
