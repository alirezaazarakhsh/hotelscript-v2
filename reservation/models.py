from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Province(models.Model):
    name = models.CharField(
        verbose_name=_('نام'),
        max_length=32,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name=_('اسلاگ'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = 'استان'
        verbose_name_plural = 'استان‌ها'

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(
        verbose_name=_('نام'),
        max_length=32,
    )
    slug = models.SlugField(
        verbose_name=_('اسلاگ'),
        max_length=32,
        unique=True,
    )
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        verbose_name=_('استان'),
        related_name='cities',
    )

    class Meta:
        verbose_name = 'شهر'
        verbose_name_plural = 'شهرها'
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "name",
                    "province",
                ],
                name="unique_name_province",
            )
        ]

    def __str__(self):
        return self.name

class HotelType(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = 'نوع هتل'
        verbose_name_plural = 'انواع هتل'

    def __str__(self):
        return self.title

class HotelTag(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name=_('اسلاگ'),
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = 'تگ'
        verbose_name_plural = 'تگ‌ها'

    def __str__(self):
        return self.title
