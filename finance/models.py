from django.db import models
from django.utils.translation import gettext_lazy as _
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
