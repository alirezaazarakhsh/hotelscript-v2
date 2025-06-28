from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
)
from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
)
from authentication.models import (
    BaseUser,
)


#  مدل کیف پول کاربر برای موجودی 
class Wallet(models.Model):
    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='wallet',
    )
    balance = models.PositiveBigIntegerField(
        verbose_name=_('موجودی'),
    )

    class Meta:
        verbose_name = 'کیف پول'
        verbose_name_plural = 'کیف پول‌ها'

    def __str__(self):
    try:
        natural_profile = self.user.natural_profile
        return f'{natural_profile.first_name or ""} {natural_profile.last_name or ""}'.strip()
    except NaturalProfile.DoesNotExist:
        return f'{self.user.email or self.user.username} (بدون پروفایل)'

    
    


#مدل کارت های بانکی کاربر
class BankCard(models.Model):
    profile_content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={
            'model__in': [
                'naturalprofile',
                'juridicalprofile',
            ],
            'app_label': 'authentication',
        },
        on_delete=models.CASCADE,
        verbose_name=_('پروفایل'),
    )
    profile_object_id = models.PositiveIntegerField()
    profile = GenericForeignKey(
        'profile_content_type',
        'profile_object_id',
    )
    card_number = models.CharField(
        verbose_name=_('شماره کارت'),
        max_length=16,
        validators=(
            MinLengthValidator(16),
            MaxLengthValidator(16),
        ),
    )
    sheba_number = models.CharField(
        verbose_name=_('شماره شبا'),
        max_length=24,
        validators=(
            MinLengthValidator(24),
            MaxLengthValidator(24),
        ),
    )

    class Meta:
        verbose_name = 'کارت بانکی'
        verbose_name_plural = 'کارت‌های بانکی'

    def __str__(self):
        return self.card_number
