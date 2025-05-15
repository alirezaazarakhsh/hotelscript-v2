from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)
from authentication.models import (
    BaseUser,
)
# Create your models here.
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
        return f'{self.user.natural_profile.first_name} {self.user.natural_profile.last_name}'

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
    )
    sheba_number = models.CharField(
        verbose_name=_('شماره شبا'),
        max_length=24,
    )

    class Meta:
        verbose_name = 'کارت بانکی'
        verbose_name_plural = 'کارت‌های بانکی'

    def __str__(self):
        return self.card_number
