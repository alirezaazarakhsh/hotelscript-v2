# 📦 استاندارد کتابخانه‌های پایتون
import logging
import os
import random
import re
from threading import local
import uuid
from decimal import Decimal, ROUND_UP
from datetime import timedelta
from django.dispatch import receiver
import jdatetime
from functools import cached_property
from jdatetime import date as jdate
from jalali_date import date2jalali
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from channels.layers import get_channel_layer
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str
from django.core.cache import cache
from bashgah_moshtarian.models import (
    CustomerClubPoint,
    DiscountActivationRecord,
    HotelDiscountCode,
    RoomDiscountCode,
    PersonalDiscountCode,
)
from config.models import UserLevel

# 🌐 Django
from django.db import models, transaction
from django.apps import apps
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum

# 🛠️ Django Model Fields و Expressions
from django.db.models import (
    Q, F, Count, Case, When,
    ExpressionWrapper, PositiveBigIntegerField,
    OuterRef, Subquery, IntegerField, CheckConstraint
)
from django.db.models.functions import Coalesce

# 🌍 Django Postgres
from django.contrib.postgres.fields import ArrayField

# 📅 Django Jalali
from django_jalali.db import models as jmodels

# 🧩 برنامه‌های داخلی پروژه
from bashgah_moshtarian.sms.sms import send_customer_club_sms, send_customer_club_deduct_sms
from finance.models import Wallet
from icons.models import IconShortcut
from authentication.models import BaseUser
from authentication.validators import (
    validate_phone_number,
    validate_national_code,
    validate_passport_code
)
from reservation.sms.sms import send_room_availability_sms

try:
    from reservation.models import RoomDate
except ImportError:
    RoomDate = None


# مدل اضافه کردن استان ها
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
        verbose_name_plural = 'اضافه کردن استان ها'
        
    def __str__(self):
        return self.name


# مدل اضافه کردن شهر ها 
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
    image = models.ImageField(
        verbose_name=_('عکس شهر'),
        upload_to='cities/',  
        null=True,
        blank=True,
    )
    province = models.ForeignKey(
        'Province',
        on_delete=models.CASCADE,
        verbose_name=_('استان'),
        related_name='cities',
    )

    show_in_homepage = models.BooleanField(
        verbose_name=_('نمایش در صفحه اصلی'),
        default=False,
    )

    class Meta:
        verbose_name = 'شهر'
        verbose_name_plural = 'اضافه کردن شهر '
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


# مدل نوع اقامتگاه
class HotelType(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = 'نوع اقامتگاه'
        verbose_name_plural = 'اضافه کردن نوع اقامتگاه'

    def __str__(self):
        return self.title


# مدل تگ های هتل صفحه داخلی 
class HotelTag(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = 'برچسب هتل'
        verbose_name_plural = 'برچسب‌ هتل'

    def __str__(self):
        return self.title


# تگ عمومی برای هتلها
class HotelTagPublic(models.Model):
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='public_tags',
    )
    title = models.CharField(
        verbose_name=_('عنوان تگ'),
        max_length=256,
    )

    class Meta:
        verbose_name = _('تگ عمومی هتل')
        verbose_name_plural = _('تگ‌های عمومی هتل')

    def __str__(self):
        return f"{self.title} ({self.hotel.name})"


# مدل سئو هتل 
class SEOMeta(models.Model):
    hotel = models.OneToOneField(
        'Hotel',
        on_delete=models.CASCADE,
        related_name='seo_meta',
        verbose_name='هتل',
        null=True,
        blank=True,
    )
    title_tag = models.CharField(
        max_length=70,
        verbose_name="عنوان سئو",
        help_text="عنوان صفحه برای سئو (حداکثر 70 کاراکتر)"
    )
    keywords = models.TextField(
        verbose_name="کلمات کلیدی",
        help_text="کلمات کلیدی را با - یا , جدا کنید. مثال: هتل-رزرو هتل-هتل های تهران",
        blank=True,
        default=""
    )
    description = models.TextField(
        max_length=160,
        verbose_name="توضیحات متا",
        help_text="توضیحات متا برای سئو (حداکثر 160 کاراکتر)"
    )

    def __str__(self):
        return f"سئو - {self.hotel.name if self.hotel else self.title_tag}"

    class Meta:
        verbose_name = "تنظیمات سئو"
        verbose_name_plural = "تنظیمات سئو"


# مدل امکانات رفاهی و تفریحی هتل 
class Facilities(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    icon = models.ForeignKey(
        'icons.IconShortcut',
        on_delete=models.CASCADE,
        verbose_name=_('آیکن'),
        related_name='facilities',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'امکانات رفاهی و تفریحی'
        verbose_name_plural = 'امکانات رفاهی و تفریحی'

    def __str__(self):
        return self.title


# مدل امکانات داخلی اتاق 
class RoomFacilities(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    icon = models.ForeignKey(
        'icons.IconShortcut',
        on_delete=models.CASCADE,
        verbose_name=_('آیکن'),
        related_name='room_facilities',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'امکانات داخل اتاق'
        verbose_name_plural = 'امکانات داخل اتاق'

    def __str__(self):
        return self.title


# مدل اضافه کردن هتل 
class Hotel(models.Model):
    def hotel_image_upload_to(instance, filename):
        return f'images/hotels/{instance.slug}/{filename}'

    name = models.CharField(
        verbose_name=_('نام'),
        max_length=256,
        blank=True,
        default='',
    )
    slug = models.SlugField(
        verbose_name=_('اسلاگ'),
        max_length=256,
        unique=True,
        blank=True,
        default='',
    )
    city = models.ForeignKey(
        'City',
        on_delete=models.CASCADE,
        verbose_name=_('شهر'),
        related_name='hotels',
        null=True,
        blank=True,
    )
    address = models.TextField(
        verbose_name=_('آدرس'),
        blank=True,
        default='',
    )
    main_image = models.ImageField(
        verbose_name=_('تصویر اصلی'),
        upload_to=hotel_image_upload_to,
        null=True,
        blank=True,
    )
    image1 = models.ImageField(
        verbose_name=_('تصویر 1'),
        upload_to=hotel_image_upload_to,
        null=True,
        blank=True,
    )
    image2 = models.ImageField(
        verbose_name=_('تصویر 2'),
        upload_to=hotel_image_upload_to,
        null=True,
        blank=True,
    )
    image3 = models.ImageField(
        verbose_name=_('تصویر 3'),
        upload_to=hotel_image_upload_to,
        null=True,
        blank=True,
    )
    image4 = models.ImageField(
        verbose_name=_('تصویر 4'),
        upload_to=hotel_image_upload_to,
        null=True,
        blank=True,
    )
    best_logo = models.ForeignKey(
        'BestHotels',
        verbose_name=_('لوگوی هتل'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hotels',
    )
    stars = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد ستاره'),
        null=True,
        blank=True,
    )
    rating = models.DecimalField(
        verbose_name=_('امتیاز هتل'),
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(Decimal('0.0')),
            MaxValueValidator(Decimal('5.0')),
        ],
        default=0.0,
    )
    reservation_count = models.PositiveIntegerField(
        verbose_name=_('تعداد رزرو هتل'),
        default=0,
        help_text=_('این مقدار فقط در نمایش هتل در قسمت هتل‌های پرفروش تاثیر دارد.')
    )
    type = models.ForeignKey(
        'HotelType',
        on_delete=models.CASCADE,
        verbose_name=_('نوع اقامتگاه'),
        related_name='hotels',
        null=True,
        blank=True,
    )
    description = models.TextField(
        verbose_name=_('توضیحات هتل'),
        blank=True,
        default='',
    )
    further_description = models.TextField(
        verbose_name=_('توضیحات تکمیلی'),
        blank=True,
        default='',
    )
    floors_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد طبقات هتل'),
        null=True,
        blank=True,
    )
    rooms_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد اتاق‌های هتل'),
        default=1,
        null=True,
        blank=True,
    )
    check_in_time = models.TimeField(
        verbose_name=_('ساعت ورود به هتل'),
        null=True,
        blank=True,
    )
    check_out_time = models.TimeField(
        verbose_name=_('ساعت خروج از هتل'),
        null=True,
        blank=True,
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
            MinValueValidator(Decimal('-90.000000')),
            MaxValueValidator(Decimal('90.000000')),
        ],
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        verbose_name=_('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal('-180.000000')),
            MaxValueValidator(Decimal('180.000000')),
        ],
        null=True,
        blank=True,
    )
    tags = models.ManyToManyField(
        'HotelTag',
        verbose_name=_('برچسب های هتل'),
        related_name='hotels',
        blank=True,
    )
    facilities = models.ManyToManyField(
        'Facilities',
        verbose_name=_('امکانات رفاهی و تفریحی'),
        related_name='hotels',
        blank=True,
    )
    room_facilities = models.ManyToManyField(
        'RoomFacilities',
        verbose_name=_('امکانات داخل اتاق'),
        related_name='hotels',
        blank=True,
    )
    is_special_offer = models.BooleanField(
        verbose_name=_('پیشنهاد ویژه صفحه اصلی'),
        default=False,
    )
    is_flash_sale = models.BooleanField(
        verbose_name=_('شگفت‌انگیز صفحه اصلی'),
        default=False,
    )
    is_best_seller = models.BooleanField(
        verbose_name=_('پرفروش‌ترین‌های صفحه اصلی'),
        default=False,
    )
    STATUS_CHOICES = [
        ('draft', _('پیش‌نویس')),
        ('published', _('منتشر شده')),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('وضعیت انتشار'),
    )
    
    snapptrip_hotel_id = models.PositiveIntegerField(
        verbose_name=_('شناسه هتل در اسنپ‌تریپ'),
        null=True,
        blank=True,
        unique=True,
    )
    sync_from_snapptrip = models.BooleanField(
        verbose_name=_('همگام‌سازی از اسنپ‌تریپ'),
        default=False,
    )
    is_snapptrip = models.BooleanField(
        verbose_name=_('هتل اسنپ‌تریپ است؟'),
        default=False
    )
    
    rules = models.TextField(
        verbose_name=_('قوانین و مقررات هتل'),
        blank=True,
        default='',
    )
    important_notes = models.TextField(
        verbose_name=_('نکات ضروری هتل'),
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'هتل'
        verbose_name_plural = 'هتل ها'

    def clean(self):
        super().clean()
        if self.status == 'published':
            required_fields = [
                'name', 'slug', 'city', 'address', 'main_image', 'stars', 'type',
                'description', 'floors_count', 'rooms_count', 'check_in_time',
                'check_out_time', 'latitude', 'longitude', 'rules'
            ]
            for field in required_fields:
                value = getattr(self, field)
                if not value:
                    raise ValidationError({field: 'این فیلد برای هتل منتشر شده ضروری است.'})

    def __str__(self):
        return self.name or 'هتل بدون نام'


class DraftHotel(Hotel):
    class Meta:
        proxy = True
        verbose_name = 'هتل پیش‌نویس'
        verbose_name_plural = 'هتل‌های پیش‌نویس'


class PublishedHotel(Hotel):
    class Meta:
        proxy = True
        verbose_name = 'هتل منتشر شده'
        verbose_name_plural = 'هتل‌های منتشر شده'

    def has_active_date_prices(self):
        today = date2jalali(timezone.now().date())
        return self.rooms.filter(
            date_prices__start_date__lte=today,
            date_prices__end_date__gte=today
        ).exists()


class HotelGallery(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان گالری'),
        max_length=256,
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='galleries',
    )

    class Meta:
        verbose_name = 'گالری تصاویر هتل'
        verbose_name_plural = ' گالری تصاویر هتل '

    def __str__(self):
        return f'{self.title} ({self.hotel})'


class HotelGalleryImage(models.Model):
    def image_upload_to(instance, filename):
        ext = filename.split('.')[-1]
        filename = f'{uuid.uuid4().hex}.{ext}'
        return os.path.join('hotel_gallery', str(instance.gallery.id), filename)

    gallery = models.ForeignKey(
        HotelGallery,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='گالری',
    )
    image = models.ImageField(
        upload_to=image_upload_to,
        verbose_name='تصویر',
    )

    class Meta:
        verbose_name = 'تصویر گالری'
        verbose_name_plural = 'تصاویر گالری'
        ordering = ['-id']

    def __str__(self):
        return f'تصویر گالری {self.gallery.title}'


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
            MinValueValidator(Decimal(-90.000000)),
            MaxValueValidator(Decimal(90.000000)),
        ],
    )
    longitude = models.DecimalField(
        verbose_name=_('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal(-180.000000)),
            MaxValueValidator(Decimal(180.000000)),
        ],
    )

    class Meta:
        verbose_name = 'مکان اطراف هتل'
        verbose_name_plural = 'اضافه کردن اماکن اطراف هتل ها'

    def __str__(self):
        return f'{self.title} - {self.hotel}'


class HotelFAQ(models.Model):
    question = models.CharField(
        verbose_name=_('سوال'),
        max_length=500,
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
    icon = models.ForeignKey(  
        IconShortcut,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('آیکون'),
        related_name='hotel_faqs',
    )

    class Meta:
        verbose_name = 'سوال متداول هتل'
        verbose_name_plural = 'سوالات متداول هتل'

    def __str__(self):
        return f'{self.hotel} - {self.question}'


class Comment(models.Model):
    user = models.ForeignKey(
        'authentication.BaseUser',
        on_delete=models.CASCADE,
        verbose_name=_('ثبت کننده'),
        related_name='comments',
    )
    hotel = models.ForeignKey(
        'reservation.Hotel',
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='comments',
    )
    text = models.TextField(
        verbose_name=_('متن'),
    )
    strengths = models.ManyToManyField(
        'reservation.CommentPointItem',
        verbose_name=_('نقاط قوت'),
        blank=True,
        related_name='comments_as_strength',
        limit_choices_to={'is_positive': True},
    )
    weaknesses = models.ManyToManyField(
        'reservation.CommentPointItem',
        verbose_name=_('نقاط ضعف'),
        blank=True,
        related_name='comments_as_weakness',
        limit_choices_to={'is_negative': True},
    )
    suggested_items = models.ManyToManyField(
        'reservation.SuggestedCommentItem',
        verbose_name=_('آیتم‌های پیشنهادی'),
        blank=True,
        related_name='comments',
    )
    stars = models.PositiveSmallIntegerField(
        verbose_name=_('امتیاز (ستاره)'),
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
    )
    is_approved = models.BooleanField(
        verbose_name=_('تایید شده'),
        default=False,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )

    @property
    def created_jalali(self):
        if self.created:
            dt = jdatetime.datetime.fromgregorian(datetime=self.created)
            return dt.strftime('%Y/%m/%d ساعت %H:%M')
        return ''

    class Meta:
        verbose_name = 'کامنت'
        verbose_name_plural = 'کامنت‌های هتل'
        ordering = ['-created']

    def __str__(self):
        return f'{self.hotel} - {self.user}'


class CommentPointItem(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    is_positive = models.BooleanField(
        verbose_name=_('نظر مثبت'),
        default=False,
    )
    is_negative = models.BooleanField(
        verbose_name=_('نظر منفی'),
        default=False,
    )

    class Meta:
        verbose_name = 'نظر منفی / نظر مثبت'
        verbose_name_plural = 'آیتم مثبت و منفی کامنت هتل ها'

    def __str__(self):
        return self.title


class SuggestedCommentItem(models.Model):
    title = models.CharField(max_length=255, verbose_name='عنوان')

    class Meta:
        verbose_name = 'پشنهاد'
        verbose_name_plural = 'آیتم پیشنهاد های کامنت هتل ها'

    def __str__(self):
        return self.title


class CommentPoint(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        verbose_name=_('کامنت'),
        related_name='points',
    )
    comment_point_item = models.ForeignKey(
        SuggestedCommentItem,
        on_delete=models.CASCADE,
        verbose_name=_('معیار امتیازدهی پیشنهادها'),
        related_name='points'
    )
    point = models.FloatField(
        verbose_name=_('امتیاز'),
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0),
        ],
    )
    
    class Meta:
        verbose_name = 'امتیاز کامنت'
        verbose_name_plural = 'امتیازهای کامنت'
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "comment",
                    "comment_point_item",
                ],
                name="unique_comment_comment_point_item",
            )
        ]

    def __str__(self):
        return str(self.comment_point_item)


class RoomService(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    
    class Meta:
        verbose_name = 'خدمات اتاق'
        verbose_name_plural = 'خدمات اتاق'

    def __str__(self):
        return self.title


logger = logging.getLogger(__name__)

class Room(models.Model):
    hotel = models.ForeignKey(
        'Hotel',
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='rooms',
        null=True,
        blank=True,
    )
    title = models.CharField(
        verbose_name=_('نام اتاق'),
        max_length=256,
        null=True,
        blank=True,
    )
    description = models.TextField(
        verbose_name=_('توضیحات در مورد اتاق'),
        blank=True,
        default='',
        null=True,
    )
    inventory = models.PositiveIntegerField(
        verbose_name=_('موجودی فعلی'),
        default=0,
    )
    count = models.PositiveIntegerField(
        verbose_name=_('ظرفیت رزرو نیازمند تأیید ادمین'),
        default=0,
        null=True,
        blank=True,
    )
    auto_approved_count = models.PositiveIntegerField(
        verbose_name=_('ظرفیت رزرو بدون تأیید ادمین'),
        default=0,
        null=True,
        blank=True,
    )
    customer_club_points = models.PositiveIntegerField(
        verbose_name=_('امتیاز باشگاه مشتریان'),
        default=0,
        null=True,
        blank=True,
    )
    room_capacity = models.PositiveIntegerField(
        verbose_name=_('ظرفیت اتاق'),
        default=0,
    )
    extra_capacity = models.PositiveIntegerField(
        verbose_name=_('ظرفیت نفر اضافه'),
        default=0,
    )
    services = models.ManyToManyField(
        'RoomService',
        verbose_name=_('خدمات'),
        related_name='rooms',
        blank=True,
    )
    image = models.ImageField(
        upload_to='room_images/',
        verbose_name=_('تصویر اتاق'),
        null=True,
        blank=True,
    )
    snapptrip_room_id = models.PositiveIntegerField(
        verbose_name=_('شناسه اتاق در اسنپ‌تریپ'),
        null=True,
        blank=True,
    )
    board_type = models.CharField(
        verbose_name=_('نوع پذیرایی (Board Type)'),
        max_length=32,
        null=True,
        blank=True,
        choices=[
            ('room_only', 'فقط اتاق'),
            ('bed_breakfast', 'با صبحانه'),
            ('half_board', 'هاف‌برد'),
            ('full_board', 'فول‌برد'),
        ],
        default='bed_breakfast'
    )
    rules = models.TextField(
        verbose_name=_('قوانین و مقررات اتاق'),
        blank=True,
        default='',
    )
    is_snapptrip = models.BooleanField(
        verbose_name=_('اتاق اسنپ‌تریپ است؟'),
        default=False
    )

    class Meta:
        verbose_name = 'اتاق'
        verbose_name_plural = 'اتاق‌ها'
        constraints = [
            models.CheckConstraint(
                check=models.Q(count__gte=0),
                name='check_admin_approved_non_negative',
            ),
            models.CheckConstraint(
                check=models.Q(auto_approved_count__gte=0),
                name='check_auto_approved_non_negative',
            ),
        ]

    def clean(self):
        super().clean()
        current_inventory = self.inventory or 0
        current_count = self.count or 0
        current_auto_approved_count = self.auto_approved_count or 0

        if current_count < 0 or current_auto_approved_count < 0:
            raise ValidationError(_('ظرفیت رزرو نمی‌تواند منفی باشد.'))
        if current_inventory < 0:
            raise ValidationError(_('موجودی نمی‌تواند منفی باشد.'))
        if current_count > current_inventory:
            raise ValidationError(_(f'ظرفیت رزرو نیازمند تأیید ادمین ({current_count}) نمی‌تواند بیشتر از موجودی فعلی باشد.'))
        if current_auto_approved_count > current_inventory:
            raise ValidationError(_(f'ظرفیت رزرو بدون تأیید ادمین ({current_auto_approved_count}) نمی‌تواند بیشتر از موجودی فعلی باشد.'))

    def __str__(self):
        return f'{self.title} - {self.hotel}' if self.hotel else self.title or 'اتاق بدون نام'

    def save(self, *args, **kwargs):
        if self.count == 0 and self.auto_approved_count == 0:
            self.inventory = 0
        super().save(*args, **kwargs)

    def is_closed(self, target_date=None):
        if target_date is None:
            target_date = jdatetime.date.today()
        active_prices = self.date_prices.filter(
            start_date__lte=target_date,
            end_date__gte=target_date
        )
        return not active_prices.exists()

    def adjust_inventory_for_reservation(self, quantity: int, auto_approval: bool):
        if quantity <= 0:
            raise ValidationError(_('تعداد رزرو باید بیشتر از صفر باشد.'))

        with transaction.atomic():
            room = Room.objects.select_for_update().get(pk=self.pk)
            if auto_approval:
                if room.auto_approved_count < quantity:
                    raise ValidationError(_('ظرفیت بدون تأیید ادمین کافی نیست.'))
                room.auto_approved_count -= quantity
            else:
                if room.count < quantity:
                    raise ValidationError(_('ظرفیت نیازمند تأیید ادمین کافی نیست.'))
                room.count -= quantity
            
            old_inventory = room.inventory
            room.inventory -= quantity
            room.save(update_fields=['inventory', 'count', 'auto_approved_count'])
            
            if old_inventory > 0 and room.inventory == 0:
                try:
                    send_room_availability_sms(
                        room_name=f"{room.title} (ID: {room.pk})",
                        status="صفر شد",
                        hotel_name=room.hotel.title if room.hotel else "نامشخص"
                    )
                except Exception as e:
                    logger.error(f"Failed to send SMS for room {room.pk}: {str(e)}")

    def revert_inventory_for_cancellation(self, quantity: int, auto_approval: bool):
        if quantity <= 0:
            raise ValidationError(_('تعداد رزرو باید بیشتر از صفر باشد.'))

        with transaction.atomic():
            room = Room.objects.select_for_update().get(pk=self.pk)
            if auto_approval:
                room.auto_approved_count += quantity
            else:
                room.count += quantity
            room.inventory += quantity
            room.save(update_fields=['inventory', 'count', 'auto_approved_count'])


class RoomDatePrice(models.Model):
    DISCOUNT_TYPES = (
        ('none', 'بدون تخفیف'),
        ('percentage', 'درصدی'),
        ('fixed', 'ثابت'),
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        verbose_name=_('اتاق'),
        related_name='date_prices',
    )
    user_level = models.ForeignKey(
        UserLevel,
        on_delete=models.CASCADE,
        verbose_name=_('سطح کاربری'),
        related_name='room_date_prices',
        blank=True,
        null=True,
    )
    start_date = jmodels.jDateField(
        verbose_name=_('تاریخ شروع بازه'),
        null=False,
        blank=False,
    )
    end_date = jmodels.jDateField(
        verbose_name=_('تاریخ پایان بازه'),
        null=False,
        blank=False,
    )
    purchase_price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت خرید اتاق (تومان)'),
        null=True,
        blank=True,
    )
    price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت هر شب (تومان)'),
        null=False,
        blank=False,
    )
    extra_passenger_price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت نفر اضافه (تومان)'),
        null=False,
        blank=False,
    )
    discount_type = models.CharField(
        verbose_name=_('نوع تخفیف'),
        max_length=16,
        choices=DISCOUNT_TYPES,
        default='none',
        blank=True,
    )
    discount_value = models.PositiveBigIntegerField(
        verbose_name=_('مقدار تخفیف'),
        default=0,
        blank=True,
    )
    discount_date = jmodels.jDateField(
        verbose_name=_('تاریخ انقضای تخفیف'),
        null=True,
        blank=True,
    )
    is_fixed_discount_one_time = models.BooleanField(
        verbose_name=_('تخفیف هنگام خرید'),
        default=False,
    )

    class Meta:
        verbose_name = _('قیمت اتاق بر اساس سطح و بازه')
        verbose_name_plural = _('بازه های زمانی اتاق')
        ordering = ['room', 'start_date', 'user_level']
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'start_date', 'end_date', 'user_level'],
                name='unique_room_date_user_level'
            ),
            models.CheckConstraint(
                check=models.Q(start_date__lte=models.F('end_date')),
                name='check_start_date_before_end_date',
            ),
        ]

    def clean(self):
        if self.discount_type == 'percentage' and (self.discount_value < 1 or self.discount_value > 100):
            raise ValidationError(_('مقدار تخفیف درصدی باید بین 1 تا 100 باشد.'))
        if self.discount_type == 'fixed' and not self.is_fixed_discount_one_time:
            raise ValidationError(_('برای تخفیف ثابت، باید گزینه "تخفیف اولین خرید" فعال باشد.'))
        if self.discount_type == 'percentage' and self.is_fixed_discount_one_time:
            raise ValidationError(_('گزینه "تخفیف اولین خرید" فقط برای تخفیف ثابت قابل استفاده است.'))
        if self.discount_type == 'percentage' and not self.discount_date:
            raise ValidationError(_('برای تخفیف درصدی، باید تاریخ انقضای تخفیف مشخص شود.'))
        if self.discount_type == 'fixed' and self.discount_date:
            raise ValidationError(_('برای تخفیف ثابت، نباید تاریخ انقضای تخفیف مشخص شود.'))
        if self.discount_date:
            if self.discount_date < self.start_date:
                raise ValidationError(_('تاریخ انقضای تخفیف نمی‌تواند قبل از تاریخ شروع بازه باشد.'))
            if self.discount_date > self.end_date:
                raise ValidationError(_('تاریخ انقضای تخفیف نمی‌تواند بعد از تاریخ پایان بازه باشد.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.room} | {self.user_level} | {self.start_date} تا {self.end_date}'


class ClosedDate(models.Model):
    room_date = models.ForeignKey(
        'RoomDatePrice',
        on_delete=models.CASCADE,
        related_name='closed_dates',
        verbose_name=_('بازه زمانی اتاق')
    )
    date = jmodels.jDateField(
        verbose_name=_('تاریخ بسته شده')
    )
    user_level = models.ForeignKey(
        'config.UserLevel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('سطح کاربری'),
    )

    class Meta:
        verbose_name = _('تاریخ بستن بازه')
        verbose_name_plural = _('تاریخ‌های بستن بازه')
        unique_together = ('room_date', 'date', 'user_level')
        ordering = ['date']

    def __str__(self):
        user_level_display = self.user_level if self.user_level else 'همه سطوح'
        return f'{self.room_date} - {self.date} - {user_level_display}'


class ReservationApprovalDuration(models.Model):
    duration_minutes = models.PositiveIntegerField(
        verbose_name=_('مدت زمان تایید رزرو (دقیقه)'),
        default=5,
    )

    class Meta:
        verbose_name = _('مدت زمان تایید رزرو')
        verbose_name_plural = _('مدت زمان‌های تایید رزرو')

    def __str__(self):
        return f'{self.duration_minutes} دقیقه'


def validate_phone_number(value):
    if not value:
        raise ValidationError(_('شماره موبایل نمی‌تواند خالی باشد.'))
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError(_('شماره موبایل باید ۱۱ رقم باشد و با 09 شروع شود. مثال: 09123456789'))


def validate_identification_code(value):
    if not value:
        raise ValidationError(_('کد شناسایی نمی‌تواند خالی باشد.'))
    if re.match(r'^\d{10}$', value):
        return value
    if 6 <= len(value) <= 9 and re.match(r'^[A-Za-z]*\d+$', value):
        return value
    raise ValidationError(_('کد شناسایی نامعتبر است. باید کد ملی ۱۰ رقمی یا شماره پاسپورت بین ۶ تا ۹ کاراکتر باشد.'))


class Passenger(models.Model):
    user = models.ForeignKey(
        'authentication.BaseUser',
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='passengers',
    )
    first_name = models.CharField(
        verbose_name=_('نام'),
        max_length=32,
    )
    last_name = models.CharField(
        verbose_name=_('نام خانوادگی'),
        max_length=32,
    )
    identification_code = models.CharField(
        verbose_name=_('کد شناسایی (کد ملی/پاسپورت)'),
        max_length=10,
        validators=[validate_identification_code],
        blank=False,
        null=True,
    )
    phone_number = models.CharField(
        verbose_name=_('موبایل'),
        max_length=11,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = _('مسافر')
        verbose_name_plural = _('مسافران')
        indexes = [
            models.Index(fields=['user', 'identification_code']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'identification_code'],
                condition=~Q(identification_code=None),
                name='unique_user_identification_code'
            )
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.identification_code})'


class BestHotels(models.Model):
    order = models.PositiveIntegerField(
        verbose_name=_("ترتیب"),
        unique=True
    )
    title_logo = models.CharField(
        verbose_name=_("عنوان لوگو"),
        max_length=128
    )
    image_logo_hotel = models.FileField(
        verbose_name=_("عکس لوگو هتل"),
        upload_to="images/best_hotels/"
    )

    class Meta:
        verbose_name = _("لوگو هتل")
        verbose_name_plural = _("لوگو هتل ها")
        ordering = ['order']

    def __str__(self):
        return f"{self.order} - {self.title_logo}"


# ---------------- Reservationhotel ----------------
class Reservationhotel(models.Model):
    CAPACITY_STATUS_CHOICES = [
        ('pending', _('در حال بررسی')),
        ('confirmed', _('تأیید رزرو')),
        ('rejected', _('رزرو رد شده')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('paid', _('پرداخت شده')),
        ('unpaid', _('پرداخت نشده')),
        ('pending', _('در انتظار پرداخت')),
    ]

    # کاربر می‌تواند نال باشد تا قبل از لاگین رزرو اولیه ساخته شود
    buyer = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر خریدار'),
        related_name='reservations',
        null=True,
        blank=True,
    )
    reserver_first_name = models.CharField(_('نام رزرو کننده'), max_length=256, blank=True, default='')
    reserver_last_name = models.CharField(_('نام خانوادگی رزرو کننده'), max_length=256, blank=True, default='')
    reserver_phone_number = models.CharField(_('شماره تماس رزرو کننده'), max_length=11, blank=True, default='')
    reserver_national_code = models.CharField(_('کد ملی رزرو کننده'), max_length=10, blank=True, null=True)

    check_in_date = jmodels.jDateField(_('تاریخ ورود'))
    check_out_date = jmodels.jDateField(_('تاریخ خروج'))

    total_price = models.DecimalField(_('مجموع قیمت'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    discount = models.DecimalField(_('تخفیف کد تخفیف'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    room_fixed_discount = models.DecimalField(_('تخفیف ثابت اتاق‌ها'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    final_price = models.DecimalField(_('قیمت نهایی'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    half_day_in_charge = models.DecimalField(_('نیم‌شارژ ورود'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    half_day_out_charge = models.DecimalField(_('نیم‌شارژ خروج'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    total_half_day_charge = models.DecimalField(_('مجموع نیم‌شارژها'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    total_extra_passenger_charge = models.DecimalField(_('مجموع قیمت نفرات اضافه'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])

    wallet_withdrawal_amount = models.DecimalField(
        _('مبلغ برداشت از کیف پول'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    wallet_withdrawn = models.BooleanField(_('برداشت از کیف پول انجام شده'), default=False)

    is_approved = models.BooleanField(_('تأیید شده'), default=False)
    tracking_code = models.CharField(max_length=20, unique=True, verbose_name='کد پیگیری رزرو')
    additional_notes = models.TextField(_('توضیحات تکمیلی'), blank=True, default='')
    capacity_status = models.CharField(_('وضعیت ظرفیت'), max_length=20, choices=CAPACITY_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(_('وضعیت پرداخت'), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    applied_discount_code = models.CharField(max_length=8, blank=True, null=True, verbose_name=_("کد تخفیف اعمال‌شده"))
    personal_discount_code = models.ForeignKey(
        'bashgah_moshtarian.PersonalDiscountCode',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='used_in_reservations',
        verbose_name=_('کد تخفیف شخصی')
    )
    personal_discount_used = models.BooleanField(_("کد تخفیف شخصی استفاده شد"), default=False)
    points_assigned = models.BooleanField(_('امتیازهای باشگاه مشتریان تخصیص داده شده'), default=False)
    discount_processed = models.BooleanField(_('پردازش کد تخفیف انجام شده'), default=False)
    ref_id = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('شناسه ارجاع تراکنش'))

    # --- فیلدهای کنسلی ---
    cancellation_penalty_applied = models.DecimalField(
        _('مبلغ جریمه کنسلی'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('مبلغی که به عنوان جریمه از مبلغ نهایی کسر شده است.')
    )
    cancellation_refunded_amount = models.DecimalField(
        _('مبلغ برگشتی به کیف پول'),
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_('مبلغ نهایی که پس از کسر جریمه به کیف پول کاربر برگشت داده شد.')
    )
    cancellation_requested = models.BooleanField(
        _('درخواست کنسلی'),
        default=False,
        help_text=_('مشخص می‌کند که کاربر درخواست کنسلی داده است.')
    )

    approval_notification_sent = models.BooleanField(
        _('اعلان تایید ارسال شده'),
        default=False,
        help_text=_('مشخص می‌کند که اعلان تایید رزرو به ادمین ارسال شده است.')
    )

    # --- فیلدهای اتصال رزرو به اسنپ‌تریپ ---
    is_snapptrip_reservation = models.BooleanField(
        default=False, 
        verbose_name=_('رزرو اسنپ‌تریپ است؟')
    )
    snapp_reservation_code = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('کد رزرو در اسنپ‌تریپ')
    )
    snapp_status = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('وضعیت رزرو در اسنپ‌تریپ')
    )

    created_at = jmodels.jDateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = jmodels.jDateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)

    class Meta:
        verbose_name = _('رزرو')
        verbose_name_plural = _('رزرو‌ها')

    def __str__(self):
        buyer_phone = self.buyer.phone_number if self.buyer else "کاربر مهمان"
        return f'رزرو {self.tracking_code} توسط {buyer_phone}'

    # --- متدهای کمکی ---
    @cached_property
    def nights_count(self):
        if self.check_in_date and self.check_out_date:
            check_in = self.check_in_date.togregorian() if hasattr(self.check_in_date, 'togregorian') else self.check_in_date
            check_out = self.check_out_date.togregorian() if hasattr(self.check_out_date, 'togregorian') else self.check_out_date
            return max(0, (check_out - check_in).days)
        return 0

    @cached_property
    def total_rooms(self):
        if not hasattr(self, 'reservation_rooms'):
            return 0
        return self.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0

    @cached_property
    def total_guests(self):
        total = 0
        if hasattr(self, 'reservation_rooms'):
            for res_room in self.reservation_rooms.all():
                if res_room.room:
                    total += (res_room.room.room_capacity + res_room.room.extra_capacity) * res_room.quantity
        return total

    def get_hotel(self):
        if hasattr(self, 'reservation_rooms') and self.reservation_rooms.exists():
            return self.reservation_rooms.first().room.hotel
        return None

    def calculate_cancellation_refund(self):
        hotel = self.get_hotel()
        if not hotel or not hasattr(hotel, 'cancellation_penalty'):
            penalty_amount = Decimal('0')
            refund_amount = self.final_price
        else:
            penalty_obj = hotel.cancellation_penalty
            penalty_percentage = Decimal(penalty_obj.penalty_percentage) / 100
            penalty_amount = (self.final_price * penalty_percentage).quantize(Decimal('1'))
            refund_amount = self.final_price - penalty_amount
        return penalty_amount, refund_amount

    def apply_cancellation_penalty(self):
        penalty_amount, refund_amount = self.calculate_cancellation_refund()
        self.cancellation_penalty_applied = penalty_amount
        self.cancellation_refunded_amount = refund_amount
        self.cancellation_requested = True
        self.save(update_fields=[
            'cancellation_penalty_applied',
            'cancellation_refunded_amount',
            'cancellation_requested'
        ])

    def calculate_total_price(self):
        if not self.pk or not self.reservation_rooms.exists():
            return (Decimal('0'),) * 9 

        first_res_room = self.reservation_rooms.first()
        if not first_res_room:
            return (Decimal('0'),) * 9

        hotel = first_res_room.room.hotel
        if not all(res_room.room.hotel == hotel for res_room in self.reservation_rooms.all()):
            raise ValidationError('تمام اتاق‌ها باید از یک هتل باشند.')

        total = Decimal('0')
        total_extra = Decimal('0')
        room_fixed_discount = Decimal('0')
        half_day_in_charge = Decimal('0')
        half_day_out_charge = Decimal('0')

        nights = self.nights_count
        if nights <= 0:
            return (total, total_extra, self.discount, half_day_in_charge, half_day_out_charge, Decimal('0'), self.discount, self.final_price, room_fixed_discount)

        user_level = getattr(self.buyer.natural_profile, 'level', None) if (self.buyer and hasattr(self.buyer, 'natural_profile')) else None
        check_in_date_std = self.check_in_date.togregorian() if hasattr(self.check_in_date, 'togregorian') else self.check_in_date

        for res_room in self.reservation_rooms.all():
            room = res_room.room
            quantity = res_room.quantity
            extra_guests = res_room.passengers.filter(passenger_type='extra').count()

            price_obj = room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level=user_level
            ).first() or room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level__isnull=True
            ).first()

            daily_price = Decimal(price_obj.price) if price_obj else Decimal('0')
            extra_price_per_person = Decimal(price_obj.extra_passenger_price) if price_obj else Decimal('0')

            total += daily_price * nights * quantity
            total_extra += extra_price_per_person * extra_guests * nights * quantity

            if price_obj and price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
                if price_obj.discount_date and check_in_date_std <= price_obj.discount_date:
                    room_fixed_discount += Decimal(price_obj.discount_value) * quantity
                elif not price_obj.discount_date:
                    room_fixed_discount += Decimal(price_obj.discount_value) * quantity

            if hasattr(res_room, 'half_day_in_selected') and res_room.half_day_in_selected and hasattr(hotel, 'has_check_in_half_day_charge') and hotel.has_check_in_half_day_charge:
                half_day_in_charge += (res_room.half_day_in_price if hasattr(res_room, 'half_day_in_price') else Decimal('0')) * quantity
            if hasattr(res_room, 'half_day_out_selected') and res_room.half_day_out_selected and hasattr(hotel, 'has_check_out_half_day_charge') and hotel.has_check_out_half_day_charge:
                half_day_out_charge += (res_room.half_day_out_price if hasattr(res_room, 'half_day_out_price') else Decimal('0')) * quantity

        total_half_day_charge = half_day_in_charge + half_day_out_charge
        base_price_after_all_discounts = total + total_extra + total_half_day_charge - self.discount - room_fixed_discount
        final_price_to_pay = base_price_after_all_discounts - self.wallet_withdrawal_amount
        
        if final_price_to_pay < 0:
            final_price_to_pay = Decimal('0')

        return (total, total_extra, self.discount, half_day_in_charge, half_day_out_charge,
                total_half_day_charge, self.discount, final_price_to_pay, room_fixed_discount)

    def save(self, *args, **kwargs):
        if not getattr(self, '_skip_price_calculation_on_save', False):
            total, total_extra, code_discount, half_in, half_out, total_half, _, final, room_fixed = self.calculate_total_price()
            self.total_price = total
            self.total_extra_passenger_charge = total_extra
            self.discount = code_discount
            self.room_fixed_discount = room_fixed
            self.half_day_in_charge = half_in
            self.half_day_out_charge = half_out
            self.total_half_day_charge = total_half
            self.final_price = final

        super().save(*args, **kwargs)


# --- متدهای کمکی پردازش کد تخفیف ---
def process_discount_after_payment_v2(self):
    if not (self.payment_status == 'paid' and self.applied_discount_code and not self.discount_processed):
        return False

    try:
        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().get(pk=self.pk)
            if reservation.discount_processed or not reservation.buyer:
                return True

            discount_obj, discount_type = find_discount_obj_by_code(reservation.applied_discount_code)
            if not discount_obj:
                return False

            if discount_type == 'personal':
                if discount_obj.user_id != reservation.buyer_id:
                    return False
                success = discount_obj.apply_use(reservation.buyer)
                if success:
                    reservation.personal_discount_code = discount_obj
                    reservation.personal_discount_used = True
                    reservation.discount_processed = True
                    reservation.save(update_fields=['personal_discount_code', 'personal_discount_used', 'discount_processed'])
                    return True
                return False

            success = discount_obj.consume_discount_for_user(reservation.buyer)
            if success:
                reservation.discount_processed = True
                reservation.save(update_fields=['discount_processed'])
                return True
            return False

    except Exception as e:
        logger.error(f"خطا در پردازش کد تخفیف: {e}")
        return False


def _debug_discount_status(self):
    try:
        discount_obj, discount_type = find_discount_obj_by_code(self.applied_discount_code)
        if not discount_obj:
            return
        logger.info(f"دیباگ کد تخفیف: {discount_obj.code} (نوع: {discount_type})")
    except Exception as e:
        logger.error(f"خطا در دیباگ کد تخفیف: {e}")


def find_discount_obj_by_code(code):
    try:
        return RoomDiscountCode.objects.get(code__iexact=code), 'room'
    except RoomDiscountCode.DoesNotExist:
        pass
    try:
        return HotelDiscountCode.objects.get(code__iexact=code), 'hotel'
    except HotelDiscountCode.DoesNotExist:
        pass
    try:
        return PersonalDiscountCode.objects.get(code__iexact=code), 'personal'
    except PersonalDiscountCode.DoesNotExist:
        pass
    return None, None


_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)


# ==============================================================================
# سیگنال مدیریت وضعیت رزرو، تایید قطعی اسنپ، کسر کیف پول و تخصیص امتیاز
# ==============================================================================
@receiver(post_save, sender=Reservationhotel)
def notify_status_change_and_assign_points(sender, instance, created, **kwargs):
    try:
        if get_skip_points_and_sms():
            return

        channel_layer = get_channel_layer()
        cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
        cache_key_points = f"points_assignment_lock_{instance.tracking_code}"
        cache_key_discount = f"discount_process_lock_{instance.tracking_code}"

        # ---------------------------------------------------------------------
        # بخش ۱: رزرو رد شده (Rejected) -> بازگردانی ظرفیت
        # ---------------------------------------------------------------------
        if instance.capacity_status == 'rejected':
            rooms = ReservationRoom.objects.filter(reservation=instance).select_related('room')
            with transaction.atomic():
                for r in rooms:
                    room = Room.objects.select_for_update().get(pk=r.room.pk)
                    room.revert_inventory_for_cancellation(r.quantity, getattr(r, 'was_auto_approved', False))
            cache.delete_many([cache_key_approval, cache_key_payment, cache_key_discount])
            logger.info(f"رزرو {instance.tracking_code} رد شد؛ ظرفیت اتاق‌ها بازگردانده شد.")

        # ---------------------------------------------------------------------
        # بخش ۲: پرداخت موفق مسافر (payment_status == 'paid')
        # ---------------------------------------------------------------------
        elif instance.payment_status == 'paid':
            logger.info(f"🔵 پرداخت موفق برای رزرو {instance.tracking_code}. شروع پردازش تایید اسنپ، کیف پول و امتیاز...")

            # الف) تایید نهایی و قطعی رزرو در وب‌سرویس اسنپ‌تریپ
            if (
                getattr(instance, 'is_snapptrip_reservation', False)
                and instance.snapp_reservation_code
                and instance.snapp_status != 'confirmed'
            ):
                try:
                    from reservation.snapptrip_service import confirm_snapptrip_booking
                    ok, final_snapp_status, msg = confirm_snapptrip_booking(instance.snapp_reservation_code)
                    if ok:
                        Reservationhotel.objects.filter(pk=instance.pk).update(snapp_status=final_snapp_status)
                        instance.snapp_status = final_snapp_status
                        logger.info(f"✅ رزرو اسنپ {instance.snapp_reservation_code} قطعی و در پنل ثبت شد: {msg}")
                    else:
                        logger.error(f"❌ خطا در قطعی کردن رزرو اسنپ ({instance.snapp_reservation_code}): {msg}")
                except Exception as snapp_confirm_err:
                    logger.error(f"❌ خطا در فراخوانی confirm اسنپ: {snapp_confirm_err}")

            # ب) کسر قطعی مبلغ برداشت‌شده از کیف پول کاربر
            if instance.buyer and instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
                with transaction.atomic():
                    res_lock = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                    if not res_lock.wallet_withdrawn and res_lock.wallet_withdrawal_amount > 0 and res_lock.buyer:
                        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=res_lock.buyer)
                        if wallet.balance >= res_lock.wallet_withdrawal_amount:
                            wallet.balance -= res_lock.wallet_withdrawal_amount
                            wallet.save(update_fields=['balance'])
                            res_lock.wallet_withdrawn = True
                            res_lock._skip_price_calculation_on_save = True
                            res_lock.save(update_fields=['wallet_withdrawn'])
                            logger.info(f"✅ مبلغ {res_lock.wallet_withdrawal_amount} تومان از کیف پول کاربر کسر شد.")
                        else:
                            logger.error(f"❌ موجودی کیف پول کاربر برای کسر کافی نیست!")

            # ج) مصرف کدهای تخفیف
            if instance.applied_discount_code and not instance.discount_processed and not cache.get(cache_key_discount):
                cache.set(cache_key_discount, True, timeout=60)
                try:
                    process_discount_after_payment_v2(instance)
                except Exception as e:
                    logger.error(f"خطا در مصرف کد تخفیف: {e}")
                finally:
                    cache.delete(cache_key_discount)

            # د) تخصیص امتیاز باشگاه مشتریان
            if instance.buyer and not instance.points_assigned and not cache.get(cache_key_points):
                cache.set(cache_key_points, True, timeout=60)
                with transaction.atomic():
                    res_pts = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                    if not res_pts.points_assigned and res_pts.buyer:
                        total_pts = sum(
                            (rr.room.customer_club_points or 0) * rr.quantity
                            for rr in res_pts.reservation_rooms.select_related('room').all()
                        )
                        if total_pts > 0:
                            club_pts, _ = CustomerClubPoint.objects.get_or_create(user=res_pts.buyer, defaults={'points': 0})
                            club_pts.points += total_pts
                            set_skip_points_and_sms(True)
                            club_pts.save()
                            set_skip_points_and_sms(False)

                            send_customer_club_sms(
                                phone_number=res_pts.buyer.phone_number,
                                user_name=res_pts.buyer.first_name or res_pts.buyer.phone_number,
                                added_points=total_pts,
                                current_points=club_pts.points
                            )
                            logger.info(f"✅ تعداد {total_pts} امتیاز باشگاه به کاربر اضافه شد.")

                        res_pts.points_assigned = True
                        res_pts.save(update_fields=['points_assigned'])

                        # افزایش مجموع خرید در پروفایل کاربر
                        if hasattr(res_pts.buyer, 'natural_profile') and res_pts.buyer.natural_profile:
                            prof = res_pts.buyer.natural_profile
                            if res_pts.final_price and res_pts.final_price > 0:
                                prof.total_purchase += res_pts.final_price
                                prof.save(update_fields=['total_purchase'])
                                prof.update_level()
                cache.delete(cache_key_points)

        # ---------------------------------------------------------------------
        # بخش ۳: ارسال وضعیت کامل و زنده به وب‌سوکت فرانت‌اند
        # ---------------------------------------------------------------------
        user_wallet = getattr(instance.buyer, 'wallet', None) if instance.buyer else None
        user_balance = int(user_wallet.balance) if user_wallet else 0
        timer_seconds = 900 if instance.capacity_status == 'confirmed' and instance.payment_status != 'paid' else None

        async_to_sync(channel_layer.group_send)(
            f"reservation_{instance.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": instance.capacity_status,
                    "payment_status": instance.payment_status,
                    "snapp_status": instance.snapp_status,
                    "final_price": int(instance.final_price or 0),
                    "wallet_balance": user_balance,
                    "timer": timer_seconds,
                },
            },
        )
        logger.debug(f"پیام به‌روزرسانی وب‌سوکت برای رزرو {instance.tracking_code} ارسال شد.")

    except Exception as e:
        logger.exception(f"خطای کلی در سیگنال رزرو {instance.tracking_code}: {e}")


# ---------------- ReservationRoom ----------------
class ReservationRoom(models.Model):
    reservation = models.ForeignKey(
        'Reservationhotel',
        on_delete=models.CASCADE,
        verbose_name='رزرو',
        related_name='reservation_rooms'
    )
    room = models.ForeignKey(
        'Room',
        on_delete=models.CASCADE,
        verbose_name='اتاق',
        related_name='reservation_rooms'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    was_auto_approved = models.BooleanField(default=False, verbose_name='رزرو خودکار تایید شد؟')
    price_per_night = models.DecimalField(
        'قیمت هر شب',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        default=Decimal('0')
    )
    extra_passenger_price = models.DecimalField(
        'قیمت هر نفر اضافه',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        default=Decimal('0'),
        blank=True,
        null=True,
    )
    fixed_discount = models.DecimalField(
        'تخفیف ثابت',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        default=Decimal('0'),
        blank=True,
        null=True,
    )
    subtotal = models.PositiveBigIntegerField(
        verbose_name='مجموع قیمت (تومان)',
        default=0
    )
    primary_passengers_count = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد نفر اصلی'
    )
    extra_passengers_count = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد نفر اضافه'
    )
    half_day_in_selected = models.BooleanField(default=False, verbose_name='نیم‌شارژ ورود انتخاب شده؟')
    half_day_out_selected = models.BooleanField(default=False, verbose_name='نیم‌شارژ خروج انتخاب شده؟')
    half_day_in_price = models.DecimalField(
        'قیمت نیم‌شارژ ورود',
        max_digits=12,
        decimal_places=0,
        default=Decimal('0'),
        validators=[MinValueValidator(0)]
    )
    half_day_out_price = models.DecimalField(
        'قیمت نیم‌شارژ خروج',
        max_digits=12,
        decimal_places=0,
        default=Decimal('0'),
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'اتاق رزرو شده'
        verbose_name_plural = 'اتاق‌های رزرو شده'

    def __str__(self):
        room_title = self.room.title if self.room_id else "اتاق نامشخص"
        reservation_code = self.reservation.tracking_code if self.reservation_id else "رزرو نامشخص"
        return f'{room_title} (تعداد: {self.quantity}) در رزرو {reservation_code}'

    def calculate_room_prices(self):
        if not self.room_id or not self.reservation_id:
            self.price_per_night = Decimal('0')
            self.extra_passenger_price = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        nights = self.reservation.nights_count
        if nights <= 0:
            self.price_per_night = Decimal('0')
            self.extra_passenger_price = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        check_in_date_std = (
            self.reservation.check_in_date.togregorian()
            if hasattr(self.reservation.check_in_date, 'togregorian')
            else self.reservation.check_in_date
        )
        user_level = getattr(self.reservation.buyer.natural_profile, 'level', None) if (self.reservation.buyer and hasattr(self.reservation.buyer, 'natural_profile')) else None

        price_obj = (
            self.room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level=user_level
            ).first()
            or self.room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level__isnull=True
            ).first()
        )

        if not price_obj:
            raise ValidationError(f"قیمت‌گذاری برای اتاق {self.room.title} در بازه زمانی مشخص‌شده یافت نشد.")

        self.price_per_night = Decimal(price_obj.price)
        self.extra_passenger_price = Decimal(price_obj.extra_passenger_price)
        if price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
            self.fixed_discount = Decimal(price_obj.discount_value)
        else:
            self.fixed_discount = Decimal('0')

        room_total = self.price_per_night * self.quantity * nights
        self.subtotal = int(room_total.quantize(Decimal('1'), rounding=ROUND_UP))

    def calculate_half_day_prices(self):
        if not self.room_id or not self.reservation_id:
            self.half_day_in_price = Decimal('0')
            self.half_day_out_price = Decimal('0')
            return

        hotel = self.room.hotel
        if not hotel:
            self.half_day_in_price = Decimal('0')
            self.half_day_out_price = Decimal('0')
            return

        if self.price_per_night <= 0:
            self.calculate_room_prices()

        half_in = Decimal('0')
        half_out = Decimal('0')

        if getattr(hotel, 'has_check_in_half_day_charge', False):
            half_in = (self.price_per_night / Decimal('2')) * self.quantity
        else:
            self.half_day_in_selected = False

        if getattr(hotel, 'has_check_out_half_day_charge', False):
            half_out = (self.price_per_night / Decimal('2')) * self.quantity
        else:
            self.half_day_out_selected = False

        self.half_day_in_price = half_in.quantize(Decimal('1'), rounding=ROUND_UP)
        self.half_day_out_price = half_out.quantize(Decimal('1'), rounding=ROUND_UP)

    def update_passenger_counts(self):
        self.primary_passengers_count = self.passengers.filter(passenger_type='primary').count()
        self.extra_passengers_count = self.passengers.filter(passenger_type='extra').count()
        self.save(update_fields=['primary_passengers_count', 'extra_passengers_count'])

    def save(self, *args, **kwargs):
        if not self.extra_passenger_price and self.room:
            check_in_date_std = (
                self.reservation.check_in_date.togregorian()
                if hasattr(self.reservation.check_in_date, 'togregorian')
                else self.reservation.check_in_date
            )
            user_level = getattr(self.reservation.buyer.natural_profile, 'level', None) if (self.reservation.buyer and hasattr(self.reservation.buyer, 'natural_profile')) else None
            price_obj = (
                self.room.date_prices.filter(
                    start_date__lte=check_in_date_std,
                    end_date__gte=check_in_date_std,
                    user_level=user_level
                ).first()
                or self.room.date_prices.filter(
                    start_date__lte=check_in_date_std,
                    end_date__gte=check_in_date_std,
                    user_level__isnull=True
                ).first()
            )
            if price_obj:
                self.extra_passenger_price = Decimal(price_obj.extra_passenger_price)

        if self.room and self.room.hotel:
            hotel = self.room.hotel
            if not getattr(hotel, 'has_check_in_half_day_charge', False):
                self.half_day_in_selected = False
                self.half_day_in_price = Decimal('0')
            if not getattr(hotel, 'has_check_out_half_day_charge', False):
                self.half_day_out_selected = False
                self.half_day_out_price = Decimal('0')

        self.calculate_room_prices()
        self.calculate_half_day_prices()
        super().save(*args, **kwargs)


# ---------------- ReservationRoomPassenger ----------------
def validate_national_code(value):
    if not value:
        raise ValidationError(_('کد شناسایی نمی‌تواند خالی باشد.'))
    if re.match(r'^\d{10}$', value):
        check_digits = int(value[9])
        total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
        if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
            raise ValidationError(_('کد ملی معتبر نیست'))
        return value
    if 6 <= len(value) <= 9 and re.match(r'^[A-Za-z]*\d+$', value):
        return value
    raise ValidationError(_('کد شناسایی نامعتبر است. باید کد ملی ۱۰ رقمی یا شماره پاسپورت بین ۶ تا ۹ کاراکتر باشد.'))


class ReservationRoomPassenger(models.Model):
    PASSENGER_TYPE_CHOICES = [
        ('primary', 'مسافر اصلی'),
        ('extra', 'نفر اضافه'),
        ('secondary', 'سایر مسافران'),
    ]

    reservation_room = models.ForeignKey(
        ReservationRoom,
        on_delete=models.CASCADE,
        related_name='passengers',
        verbose_name='اتاق رزرو شده'
    )
    passenger_type = models.CharField(
        max_length=20,
        choices=PASSENGER_TYPE_CHOICES,
        verbose_name='نوع مسافر'
    )
    is_primary = models.BooleanField(default=False, verbose_name='مسافر اصلی است؟')
    first_name = models.CharField('نام', max_length=100)
    last_name = models.CharField('نام خانوادگی', max_length=100)
    mobile_number = models.CharField('شماره موبایل', max_length=11, blank=True, null=True)
    national_code = models.CharField('کد ملی', max_length=10, blank=True, null=True, validators=[validate_national_code])

    class Meta:
        verbose_name = 'مسافر'
        verbose_name_plural = 'مسافرها'

    def clean(self):
        if self.passenger_type == 'primary':
            missing_fields = []
            for field_name in ['first_name', 'last_name']:
                if not getattr(self, field_name):
                    missing_fields.append(field_name)
            if missing_fields:
                raise ValidationError(f'برای مسافر اصلی، فیلدهای {missing_fields} الزامی هستند.')

        if self.national_code:
            validate_national_code(self.national_code)

    def save(self, *args, **kwargs):
        self.is_primary = self.passenger_type == 'primary'
        self.full_clean()
        super().save(*args, **kwargs)
        if self.reservation_room:
            self.reservation_room.update_passenger_counts()
            if self.reservation_room.reservation:
                self.reservation_room.reservation.save()

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.get_passenger_type_display()})'


# دلایل کنسلی رزرو 
class CancellationReason(models.Model):
    title = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name="عنوان کنسلی",
    )

    class Meta:
        verbose_name = "دلیل کنسلی"
        verbose_name_plural = "دلایل کنسلی"

    def __str__(self):
        return self.title


# مدل کنسلی رزرو توسط کاربر
# مدل کنسلی رزرو توسط کاربر
class UserCancellation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('در انتظار بررسی')
        APPROVED = 'approved', _('تایید شده')
        REJECTED = 'rejected', _('عدم تایید')

    reservation = models.ForeignKey(
        Reservationhotel,
        on_delete=models.CASCADE,
        related_name='cancellations',
        verbose_name=_('رزرو مرتبط')
    )
    reasons = models.ManyToManyField(
        CancellationReason,
        verbose_name=_('دلایل کنسلی')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('توضیحات')
    )
    PENALTY_TYPE_CHOICES = (
        ('hotel_default', _('استفاده از تنظیمات هتل')),
        ('percentage', _('درصدی')),
        ('fixed', _('مبلغ ثابت')),
    )
    penalty_type = models.CharField(
        max_length=20,
        choices=PENALTY_TYPE_CHOICES,
        default='hotel_default',
        verbose_name=_('نوع جریمه'),
    )
    penalty_value = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_('مقدار جریمه'),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('وضعیت')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))

    def __str__(self):
        return f"{self.reservation.tracking_code} - {self.status}"

    def clean(self):
        super().clean()
        if self.penalty_type == 'percentage':
            if self.penalty_value is None:
                raise ValidationError({'penalty_value': _('درصد جریمه مشخص نشده است.')})
            if self.penalty_value < 0 or self.penalty_value > 100:
                raise ValidationError({'penalty_value': _('درصد جریمه باید بین 0 تا 100 باشد.')})
        elif self.penalty_type == 'fixed':
            if self.penalty_value is None:
                raise ValidationError({'penalty_value': _('مبلغ جریمه مشخص نشده است.')})
            if self.penalty_value < 0:
                raise ValidationError({'penalty_value': _('مبلغ جریمه نمی‌تواند منفی باشد.')})

    class Meta:
        verbose_name = _('کنسل رزرو کاربر')
        verbose_name_plural = _('کنسل رزروهای کاربران')

    def process_cancellation(self):
        if self.status != self.Status.APPROVED:
            raise ValidationError(_('فقط درخواست‌های تایید شده قابل پردازش هستند.'))

        reservation = self.reservation
        hotel = reservation.get_hotel()
        if not hotel:
            raise ValidationError(_('هتل مرتبط با رزرو یافت نشد.'))

        final_price = reservation.final_price
        penalty_amount = Decimal('0')

        if self.penalty_type == 'hotel_default':
            try:
                penalty_obj = CancellationPenalty.objects.get(hotel=hotel)
            except CancellationPenalty.DoesNotExist:
                penalty_amount = Decimal('0')
            else:
                penalty_percentage = Decimal(penalty_obj.penalty_percentage) / 100
                penalty_amount = (final_price * penalty_percentage).quantize(Decimal('1'), rounding=ROUND_UP)

        elif self.penalty_type == 'percentage':
            if self.penalty_value is None:
                raise ValidationError(_('درصد جریمه مشخص نشده است.'))
            if self.penalty_value < 0 or self.penalty_value > 100:
                raise ValidationError(_('درصد جریمه باید بین 0 تا 100 باشد.'))
            penalty_percentage = Decimal(self.penalty_value) / 100
            penalty_amount = (final_price * penalty_percentage).quantize(Decimal('1'), rounding=ROUND_UP)

        elif self.penalty_type == 'fixed':
            if self.penalty_value is None:
                raise ValidationError(_('مبلغ جریمه مشخص نشده است.'))
            if self.penalty_value < 0:
                raise ValidationError(_('مبلغ جریمه نمی‌تواند منفی باشد.'))
            penalty_amount = Decimal(self.penalty_value)

        refund_amount = max(Decimal('0'), final_price - penalty_amount)

        with transaction.atomic():
            deducted_points = 0
            if getattr(reservation, 'points_assigned', False) and reservation.buyer:
                total_points = 0
                for res_room in reservation.reservation_rooms.select_related('room').all():
                    room = res_room.room
                    quantity = res_room.quantity
                    points = room.customer_club_points or 0
                    total_points += points * quantity

                if total_points > 0:
                    customer_points, created = CustomerClubPoint.objects.select_for_update().get_or_create(
                        user=reservation.buyer,
                        defaults={'points': 0}
                    )
                    prev = customer_points.points
                    deducted_points = min(prev, total_points)
                    customer_points.points = prev - deducted_points
                    customer_points.save()

            if reservation.buyer:
                wallet, created = Wallet.objects.get_or_create(user=reservation.buyer)
                wallet.balance += refund_amount
                wallet.save()

            reservation.cancellation_penalty_applied = penalty_amount
            reservation.cancellation_refunded_amount = refund_amount
            reservation.cancellation_requested = True
            reservation.payment_status = 'unpaid'
            if deducted_points > 0:
                reservation.points_assigned = False

            try:
                set_skip_points_and_sms(True)
                update_fields = [
                    'cancellation_penalty_applied',
                    'cancellation_refunded_amount',
                    'cancellation_requested',
                    'payment_status',
                ]
                if deducted_points > 0:
                    update_fields.append('points_assigned')
                reservation.save(update_fields=update_fields)
            finally:
                set_skip_points_and_sms(False)

            if deducted_points > 0 and reservation.buyer:
                try:
                    send_customer_club_deduct_sms(
                        reservation.buyer.phone_number,
                        reservation.buyer.first_name or reservation.buyer.phone_number,
                        deducted_points,
                        customer_points.points
                    )
                except Exception:
                    logger.exception('خطا هنگام ارسال اس‌ام‌اس کسر امتیاز')

        return {
            'penalty_amount': penalty_amount,
            'refund_amount': refund_amount,
            'final_price': final_price
        }

# مدل جریمه کنسلی (برای هر هتل)
class CancellationPenalty(models.Model):
    hotel = models.OneToOneField(
        Hotel,  
        on_delete=models.CASCADE,
        related_name='cancellation_penalty',
        verbose_name=_('هتل')
    )
    penalty_percentage = models.PositiveSmallIntegerField(
        _('درصد جریمه کنسلی'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        verbose_name = _('جریمه کنسلی هتل')
        verbose_name_plural = _('تنظیمات جریمه هتل ها')

    def __str__(self):
        return f"{self.hotel.name} - {self.penalty_percentage}%"

    def clean(self):
        if self.penalty_percentage > 100:
            raise ValidationError(_('درصد جریمه نمی‌تواند بیشتر از ۱۰۰ باشد.'))


# تنظیمات فاکتور رزرو 
class ReservationInvoiceSettings(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name="عنوان زیر امضا"
    )
    signature_image = models.ImageField(
        upload_to='signatures/',
        verbose_name="تصویر امضا",
        blank=True,
        null=True
    )
    contact_number_1 = models.CharField(
        max_length=15,
        verbose_name="شماره تماس ۱"
    )
    contact_number_2 = models.CharField(
        max_length=15,
        verbose_name="شماره تماس ۲",
        blank=True,
        null=True
    )
    postal_address = models.CharField(
        max_length=300,
        verbose_name="آدرس پستی",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "تنظیمات فاکتور رزرو"
        verbose_name_plural = "تنظیمات فاکتور رزرو"

    def __str__(self):
        return self.title


# ---------------- تنظیمات وب‌سرویس اسنپ‌تریپ ----------------
class SnappTripSetting(models.Model):
    title = models.CharField(
        max_length=100, 
        default="تنظیمات وب‌سرویس اسنپ‌تریپ", 
        verbose_name=_("عنوان")
    )
    base_url = models.URLField(
        default="https://b2bapiv2.snapptrip.com", 
        verbose_name=_("آدرس پایه (Base URL)")
    )
    swagger_url = models.URLField(
        default="https://b2bapiv2.snapptrip.com/swagger/index.html#/", 
        verbose_name=_("آدرس سواگر (Swagger Link)")
    )
    api_key = models.CharField(
        max_length=256, 
        blank=True, 
        null=True, 
        verbose_name=_("کلید وب‌سرویس (API Key)"),
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("وضعیت اتصال فعال باشد؟")
    )

    class Meta:
        verbose_name = _("تنظیمات API اسنپ‌تریپ")
        verbose_name_plural = _("تنظیمات API اسنپ‌تریپ")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


# ---------------- بانک اطلاعات هتل‌های اسنپ‌تریپ ----------------
class SnappHotelDirectory(models.Model):
    snapp_hotel_id = models.PositiveIntegerField(
        unique=True, 
        verbose_name=_('شناسه هتل در اسنپ')
    )
    name = models.CharField(
        max_length=256, 
        verbose_name=_('نام هتل در اسنپ')
    )
    city_name = models.CharField(
        max_length=128, 
        verbose_name=_('شهر'), 
        blank=True, 
        default=''
    )
    city_id = models.PositiveIntegerField(
        verbose_name=_('شناسه شهر در اسنپ'), 
        null=True, 
        blank=True
    )
    stars = models.CharField(
        max_length=32, 
        verbose_name=_('تعداد ستاره'), 
        blank=True, 
        default='-'
    )
    last_synced = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('آخرین بروزرسانی')
    )

    class Meta:
        verbose_name = _('هتل اسنپ‌تریپ')
        verbose_name_plural = _('بانک هتل‌های اسنپ‌تریپ')
        ordering = ['city_name', 'name']

    def __str__(self):
        return f"{self.name} ({self.snapp_hotel_id}) - {self.city_name}"