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
class Favorite(models.Model):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
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
