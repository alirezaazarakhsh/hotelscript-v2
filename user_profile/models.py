from django.db import models
from django.utils.translation import gettext_lazy as _
from authentication.models import (
    BaseUser,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
)

# Create your models here.
class FavoriteCollection(models.Model):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='favorite_lists',
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )

    class Meta:
        verbose_name = 'لیست علاقمندی'
        verbose_name_plural = 'لیست‌های علاقمندی'

    def __str__(self):
        return f'{self.title}'

class Favorite(models.Model):
    list = models.ForeignKey(
        FavoriteCollection,
        on_delete=models.CASCADE,
        verbose_name=_('لیست'),
        related_name='favorites',
    )
    item_content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={
            'model__in': [
                'article',
                'hotel',
            ], 
            'app_label__in': [
                'blog',
                'reservation',
            ]
        },
        on_delete=models.CASCADE,
        verbose_name=_('آیتم'),
    )
    item_object_id = models.PositiveIntegerField()
    item = GenericForeignKey(
        'item_content_type',
        'item_object_id',
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'علاقمندی'
        verbose_name_plural = 'علاقمندی‌ها'

    def __str__(self):
        return f'{self.item} - {self.list}'

class CustomerClub(models.Model):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='club',
    )
    points = models.PositiveIntegerField(
        verbose_name=_('امتیاز'),
    )

    class Meta:
        verbose_name = 'باشگاه مشتری'
        verbose_name_plural = 'باشگاه مشتریان'

    def __str__(self):
        return f'{self.user} - {self.points}'

class CustomerClubPrize(models.Model):
    PRIZE_TYPES = (
        ('hotel', 'هتل'),
        ('shopping-center', 'مرکز خرید'),
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    type = models.CharField(
        verbose_name=_('نوع'),
        max_length=32,
        choices=PRIZE_TYPES,
    )
    required_points = models.PositiveIntegerField(
        verbose_name=_('امتیاز مورد نیاز'),
    )
    expired_date = models.DateTimeField(
        verbose_name=_('تاریخ اعتبار کد تخفیف'),
    )
    discount_price = models.PositiveBigIntegerField(
        verbose_name=_('مبلغ تخفیف'),
    )
    discount_code = models.CharField(
        verbose_name=_('کد تخفیف'),
        max_length=64,
    )
    rules = models.TextField(
        verbose_name=_('قوانین دریافت جایزه'),
    )

    class Meta:
        verbose_name = 'جایزه باشگاه مشتریان'
        verbose_name_plural = 'جوایز باشگاه مشتریان'

    def __str__(self):
        return f'{self.title}'

class CustomerClubPrize(models.Model):
    PRIZE_TYPES = (
        ('hotel', 'هتل'),
        ('shopping-center', 'مرکز خرید'),
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    type = models.CharField(
        verbose_name=_('نوع'),
        max_length=32,
        choices=PRIZE_TYPES,
    )
    required_points = models.PositiveIntegerField(
        verbose_name=_('امتیاز مورد نیاز'),
    )
    expired_date = models.DateTimeField(
        verbose_name=_('تاریخ اعتبار کد تخفیف'),
    )
    discount_price = models.PositiveBigIntegerField(
        verbose_name=_('مبلغ تخفیف'),
    )
    discount_code = models.CharField(
        verbose_name=_('کد تخفیف'),
        max_length=64,
    )
    rules = models.TextField(
        verbose_name=_('قوانین دریافت جایزه'),
    )

    class Meta:
        verbose_name = 'جایزه باشگاه مشتریان'
        verbose_name_plural = 'جوایز باشگاه مشتریان'

    def __str__(self):
        return f'{self.title}'

class CustomerReceivedPrize(models.Model):
    customer = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('مشتری'),
    )
    prize = models.ForeignKey(
        CustomerClubPrize,
        on_delete=models.CASCADE,
        verbose_name=_('جایزه'),
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ دریافت'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'جایزه دریافت شده مشتریان'
        verbose_name_plural = 'جوایز دریافت شده مشتریان'
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'customer',
                    'prize',
                ],
                name='unique_customer_prize'
            )
        ]

    def __str__(self):
        return f'{self.customer} - {self.prize}'
