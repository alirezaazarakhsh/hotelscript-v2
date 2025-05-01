from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.contrib.postgres.fields import ArrayField
from authentication.models import (
    BaseUser,
)

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

class Facilities(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = 'امکانات رفاهی و تفریحی'
        verbose_name_plural = 'امکانات رفاهی و تفریحی'

    def __str__(self):
        return self.title

class RoomFacilities(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = 'امکانات داخل اتاق'
        verbose_name_plural = 'امکانات داخل اتاق'

    def __str__(self):
        return self.title

class Hotel(models.Model):
    
    def hotel_image_upload_to(instance, filename):
        return f'images/hotels/{instance.slug}/{filename}'

    name = models.CharField(
        verbose_name=_('نام'),
        max_length=256,
    )
    slug = models.SlugField(
        verbose_name=_('اسلاگ'),
        max_length=256,
        unique=True,
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name=_('شهر'),
        related_name='hotels',
    )
    address = models.TextField(
        verbose_name=_('آدرس'),
    )
    main_image = models.ImageField(
        verbose_name=_('تصویر اصلی'),
        upload_to=hotel_image_upload_to,
    )
    image1 = models.ImageField(
        verbose_name=_('تصویر 1'),
        upload_to=hotel_image_upload_to,
    )
    image2 = models.ImageField(
        verbose_name=_('تصویر 2'),
        upload_to=hotel_image_upload_to,
    )
    image3 = models.ImageField(
        verbose_name=_('تصویر 3'),
        upload_to=hotel_image_upload_to,
    )
    image4 = models.ImageField(
        verbose_name=_('تصویر 4'),
        upload_to=hotel_image_upload_to,
    )
    image5 = models.ImageField(
        verbose_name=_('تصویر 5'),
        upload_to=hotel_image_upload_to,
    )
    image6 = models.ImageField(
        verbose_name=_('تصویر 6'),
        upload_to=hotel_image_upload_to,
    )
    stars = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد ستاره'),
    )
    type = models.ForeignKey(
        HotelType,
        on_delete=models.CASCADE,
        verbose_name=_('نوع هتل'),
        related_name='hotels',
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
    )
    further_description = models.TextField(
        verbose_name=_('توضیحات تکمیلی'),
        blank=True,
        default='',
    )
    floors_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد طبقات'),
    )
    check_in_time = models.TimeField(
        verbose_name=_('ساعت ورود'),
    )
    check_out_time = models.TimeField(
        verbose_name=_('ساعت خروج'),
    )
    has_check_in_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ ورود'),
    )
    has_check_out_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ خروج'),
    )
    latitude = models.DecimalField(
        verbose_name=_('عرض جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-90.000000),
            MaxValueValidator(90.000000),
        ],
    )
    longitude = models.DecimalField(
        verbose_name=_('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-180.000000),
            MaxValueValidator(180.000000),
        ],
    )
    tags = models.ManyToManyField(
        HotelTag,
        verbose_name=_('تگ'),
        related_name='hotels',
    )
    facilities = models.ManyToManyField(
        Facilities,
        verbose_name=_('امکانات رفاهی و تفریحی'),
        related_name='hotels',
    )
    room_facilities = models.ManyToManyField(
        RoomFacilities,
        verbose_name=_('امکانات داخل اتاق'),
        related_name='hotels',
    )
    is_special_offer = models.BooleanField(
        verbose_name=_('پیشنهاد ویژه'),
    )
    rules = models.TextField(
        verbose_name=_('قوانین'),
    )
    important_notes = models.TextField(
        verbose_name=_('نکات ضروری'),
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'هتل'
        verbose_name_plural = 'هتل‌ها'

    def __str__(self):
        return self.name

class HotelGallery(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=256,
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='galleries',
    )

    class Meta:
        verbose_name = 'گالری هتل'
        verbose_name_plural = 'گالری‌های هتل'

    def __str__(self):
        return f'{self.title} - {self.hotel}'

class HotelGalleryImage(models.Model):

    def image_upload_to(instance, filename):
        return f'images/hotel-gallery/{instance.gallery.pk}/{filename}'

    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=256,
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to=image_upload_to,
    )
    gallery = models.ForeignKey(
        HotelGallery,
        on_delete=models.CASCADE,
        verbose_name=_('گالری'),
        related_name='images',
    )

    class Meta:
        verbose_name = 'عکس گالری هتل'
        verbose_name_plural = 'عکس‌های گالری هتل'

    def __str__(self):
        return self.title

class NearbyPlace(models.Model):

    def image_upload_to(instance, filename):
        return f'images/nearby-places/{instance.hotel.pk}/{filename}'

    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=256,
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='nearby_places',
    )
    distance = models.PositiveIntegerField(
        verbose_name=_('مسافت (به متر)'),
    )
    driving_time = models.PositiveSmallIntegerField(
        verbose_name=_('زمان با ماشین (به دقیقه)')
    )
    walking_time = models.PositiveSmallIntegerField(
        verbose_name=_('زمان پیاده روی (به دقیقه)')
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to=image_upload_to,
    )
    latitude = models.DecimalField(
        verbose_name=_('عرض جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-90.000000),
            MaxValueValidator(90.000000),
        ],
    )
    longitude = models.DecimalField(
        verbose_name=_('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-180.000000),
            MaxValueValidator(180.000000),
        ],
    )

    class Meta:
        verbose_name = 'مکان اطراف هتل'
        verbose_name_plural = 'اماکن اطراف هتل'

    def __str__(self):
        return f'{self.title} - {self.hotel}'

class HotelFAQ(models.Model):
    question = models.TextField(
        verbose_name=_('سوال'),
    )
    answer = models.TextField(
        verbose_name=_('جواب'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='faqs',
    )

    class Meta:
        verbose_name = 'سوال متداول هتل'
        verbose_name_plural = 'سوالات متداول هتل'

    def __str__(self):
        return f'{self.hotel} - {self.question}'

class Comment(models.Model):
    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('ثبت کننده'),
        related_name='comments',
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='comments',
    )
    text = models.TextField(
        verbose_name=_('متن'),
    )
    strengths = ArrayField(
        models.TextField(),
        verbose_name=_('نقاط قوت'),
        blank=True,
        default=list,
    )
    weaknesses = ArrayField(
        models.TextField(),
        verbose_name=_('نقاط ضعف'),
        blank=True,
        default=list,
    )
    is_approved = models.BooleanField(
        verbose_name=_('تایید شده'),
        default=False,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )
    
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'

    def __str__(self):
        return f'{self.hotel} - {self.user}'
