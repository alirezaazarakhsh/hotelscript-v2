from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class FavoriteCollection(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # استفاده از مدل کاربر سفارشی
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='favorite_lists',
    )
    title = models.CharField(
        verbose_name=_('نام لیست'),
        max_length=128,
    )

    class Meta:
        verbose_name = 'لیست علاقمندی'
        verbose_name_plural = 'لیست‌های علاقمندی'

    def __str__(self):
      return f"{self.title} - {self.user}"
  
  
  
  
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
            'model__in': ['article', 'hotel'],
            'app_label__in': ['blog', 'reservation']
        },
        on_delete=models.CASCADE,
        verbose_name=_('آیتم'),
    )
    item_object_id = models.PositiveIntegerField()
    item = GenericForeignKey(
        'item_content_type',
        'item_object_id',
    )
    

    class Meta:
        verbose_name = 'علاقمندی'
        verbose_name_plural = 'علاقمندی‌ها'

    def __str__(self):
        return f'{self.item} - {self.list}'