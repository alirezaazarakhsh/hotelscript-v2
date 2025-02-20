from django.db import models
from django.utils.translation import gettext_lazy as _
from authentication.validators import (
    validate_phone_number,
)

# Create your models here.
class ContactMessage(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    full_name = models.CharField(
        verbose_name=_('نام و نام خانوادگی'),
        max_length=64,
    )
    phone_number = models.CharField(
        verbose_name=_('شماره موبایل'),
        max_length=11,
        validators=(
            validate_phone_number,
        )
    )
    email = models.EmailField(
        verbose_name=_('ایمیل'),
        max_length=128,
    )
    text = models.TextField(
        verbose_name=_('متن'),
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'پیام تماس با ما'
        verbose_name_plural = 'پیام‌های تماس با ما'
    
    def __str__(self):
        return f'{self.title}'
