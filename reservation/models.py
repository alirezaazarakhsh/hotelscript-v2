# 📦 استاندارد کتابخانه‌های پایتون
import logging
import os
import random
import re
import uuid
from decimal import Decimal, ROUND_UP
from datetime import timedelta
import jdatetime
from functools import cached_property
from jdatetime import date as jdate

# 🌐 Django
from django.db import models
from django.apps import apps
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum 
from jdatetime import date as jdate



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
from config.models import UserLevel
from icons.models import IconShortcut
from authentication.models import BaseUser
from authentication.validators import (
    validate_phone_number,
    validate_national_code,
    validate_passport_code
)
from reservation.sms.sms import send_room_availability_sms

# اگر RoomDate در همین فایل نیست و نیاز است ایمپورت شود:
try:
    from reservation.models import RoomDate
except ImportError:
    RoomDate = None  # یا حذف کنید و در تعریف فیلدها از 'reservation.RoomDate' به صورت رشته استفاده کنید





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
        'Province',  # 
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






#مدل نوع اقامتگاه
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






#مدل تگ های هتل صفحه داخلی 
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





#تگ عمومی برای هتلها
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




#مدل لمکانات رفاهی و تفریحی هتل 
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
        related_name='facilities',  # Changed to avoid conflict with RoomFacilities
        null=True,  # Allow null temporarily
        blank=True  # Optional in admin forms
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
        null=True,  # Allow null temporarily
        blank=True  # Optional in admin forms
    )

    class Meta:
        verbose_name = 'امکانات داخل اتاق'
        verbose_name_plural = 'امکانات داخل اتاق'

    def __str__(self):
        return self.title







#مدل اضافه کردن هتل 
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
        'City',
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
        help_text=_('این مقدار فقط در نمایش هتل در قسمت هتل‌های پرفروش تاثیر دارد و در بخش‌های دیگر تاثیری نخواهد داشت.')
    )
    type = models.ForeignKey(
        'HotelType',
        on_delete=models.CASCADE,
        verbose_name=_('نوع اقامتگاه'),
        related_name='hotels',
    )
    description = models.TextField(
        verbose_name=_('توضیحات هتل'),
    )
    further_description = models.TextField(
        verbose_name=_('توضیحات تکمیلی'),
        blank=True,
        default='',
    )
    floors_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد طبقات هتل'),
    )
    rooms_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد اتاق‌های هتل'),
        default=1,
    )
    check_in_time = models.TimeField(
        verbose_name=_('ساعت ورود به هتل'),
    )
    check_out_time = models.TimeField(
        verbose_name=_('ساعت خروج از هتل'),
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
    )
    longitude = models.DecimalField(
        verbose_name=_('طول جغرافیایی'),
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal('-180.000000')),
            MaxValueValidator(Decimal('180.000000')),
        ],
    )
    tags = models.ManyToManyField(
        'HotelTag',
        verbose_name=_('برچسب های هتل'),
        related_name='hotels',
    )
    facilities = models.ManyToManyField(
        'Facilities',
        verbose_name=_('امکانات رفاهی و تفریحی'),
        related_name='hotels',
    )
    room_facilities = models.ManyToManyField(
        'RoomFacilities',
        verbose_name=_('امکانات داخل اتاق'),
        related_name='hotels',
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
    rules = models.TextField(
        verbose_name=_('قوانین و مقررات هتل'),
    )
    important_notes = models.TextField(
        verbose_name=_('نکات ضروری هتل'),
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'هتل'
        verbose_name_plural = 'هتل ها'

    def __str__(self):
        return self.name





#مدل گالری های هتل 
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





#مدل عکس های گالری تصاویر هتل
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
    order = models.PositiveIntegerField(
        verbose_name='ترتیب نمایش',
        default=0,
    )

    class Meta:
        verbose_name = 'تصویر گالری'
        verbose_name_plural = 'تصاویر گالری'
        ordering = ['order']

    def __str__(self):
        return f'تصویر #{self.id} از گالری {self.gallery}'
        return self.title






#مدل اماکن اطراف هتل 
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








# مدل سوالات متداول برای هر هتل
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








#مدل نظرات هتل ها 
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
        help_text=_('متن کامل نظر کاربر درباره هتل')
    )

    strengths = models.ManyToManyField(
        'reservation.CommentPointItem',
        verbose_name=_('نقاط قوت'),
        blank=True,
        related_name='comments_as_strength',
        limit_choices_to={'is_positive': True},
        help_text=_('موارد مثبتی که کاربر درباره هتل گفته')
    )

    weaknesses = models.ManyToManyField(
        'reservation.CommentPointItem',
        verbose_name=_('نقاط ضعف'),
        blank=True,
        related_name='comments_as_weakness',
        limit_choices_to={'is_negative': True},
        help_text=_('موارد منفی که کاربر درباره هتل گفته')
    )

    suggested_items = models.ManyToManyField(
        'reservation.SuggestedCommentItem',
        verbose_name=_('آیتم‌های پیشنهادی'),
        blank=True,
        related_name='comments',
        help_text=_('آیتم‌های پیشنهادی برای نوشتن کامنت راحت‌تر')
    )

    stars = models.PositiveSmallIntegerField(
        verbose_name=_('امتیاز (ستاره)'),
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text=_('امتیاز باید بین ۱ تا ۵ باشد')
    )

    is_approved = models.BooleanField(
        verbose_name=_('تایید شده'),
        default=False,
        help_text=_('آیا کامنت توسط ادمین تایید شده؟')
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
    
    
    
    
    
    
#مدل معیار امتیاز دهی
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
    
    
    
    
    

    
# مدل اضافه کردن نظر پیشنهادی برای هر هتل 
class SuggestedCommentItem(models.Model):
    title = models.CharField(max_length=255,verbose_name='عنوان')

    class Meta:
        verbose_name = 'پشنهاد'
        verbose_name_plural = 'آیتم پیشنهاد های کامنت هتل ها'

    def __str__(self):
        return self.title






#مدل امتیاز کامنت ها 
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







#مدل خدمات اتاق ها
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
    
    




#مدل اتاق ها 
# تنظیم logging
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
        help_text=_('تعداد اتاق‌های قابل رزرو در حال حاضر'),
        default=0,
    )

    count = models.PositiveIntegerField(
        verbose_name=_('تعداد رزرو نیازمند تایید ادمین'),
        help_text=_('تعداد رزروهایی که باید تایید ادمین داشته باشند'),
        default=0,
        null=True,
        blank=True,
    )
    auto_approved_count = models.PositiveIntegerField(
        verbose_name=_('تعداد رزرو بدون تایید ادمین'),
        help_text=_('تعداد رزروهایی که بدون تایید ادمین تایید می‌شوند'),
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
        help_text=_('تعداد نفرات پایه قابل اقامت'),
        null=False,
        blank=False,
        default=0,
    )
    extra_capacity = models.PositiveIntegerField(
        verbose_name=_('ظرفیت نفر اضافه'),
        help_text=_('تعداد نفرات اضافی مجاز'),
        null=False,
        blank=False,
        default=0,
    )
    services = models.ManyToManyField(
        'RoomService',
        verbose_name=_('خدمات'),
        related_name='rooms',
        blank=True,
    )

    class Meta:
        verbose_name = 'اتاق'
        verbose_name_plural = 'اتاق ها'
        constraints = [
            models.CheckConstraint(
                check=models.Q(count__gte=0),
                name='check_admin_approved_non_negative',
            ),
            models.CheckConstraint(
                check=models.Q(auto_approved_count__gte=0),
                name='check_auto_approved_non_negative',
            ),
            models.CheckConstraint(
                check=models.Q(count__lte=models.F('inventory')),
                name='count_lte_inventory',
            ),
            models.CheckConstraint(
                check=models.Q(auto_approved_count__lte=models.F('inventory')),
                name='auto_count_lte_inventory',
            ),
        ]

    def clean(self):
        super().clean()
        current_inventory = self.inventory or 0
        current_count = self.count or 0
        current_auto_approved_count = self.auto_approved_count or 0
        if current_count + current_auto_approved_count > current_inventory:
            raise ValidationError({
                'count': _('جمع تعداد رزروهای تایید شده و بدون تایید نمی‌تواند بیشتر از موجودی باشد.'),
                'auto_approved_count': _('جمع تعداد رزروهای تایید شده و بدون تایید نمی‌تواند بیشتر از موجودی باشد.'),
            })

    def __str__(self):
        return f'{self.title} - {self.hotel}' if self.hotel else self.title or 'اتاق بدون نام'

    def is_closed(self, target_date=None):
        if target_date is None:
            target_date = JalaliDate.today()
        active_prices = self.date_prices.filter(
            start_date__lte=target_date,
            end_date__gte=target_date
        )
        return not active_prices.exists()

    def save(self, *args, **kwargs):
        old_instance = None
        old_inventory = None
        old_count = None
        old_auto_approved_count = None

        if self.pk:
            try:
                old_instance = Room.objects.get(pk=self.pk)
                old_inventory = old_instance.inventory or 0
                old_count = old_instance.count or 0
                old_auto_approved_count = old_instance.auto_approved_count or 0
                logger.debug(f"Room {self.pk}: Old inventory = {old_inventory}, Old count = {old_count}, Old auto_approved_count = {old_auto_approved_count}")
            except Room.DoesNotExist:
                logger.error(f"Room with pk {self.pk} not found during save")

        current_inventory = self.inventory or 0
        current_count = self.count or 0
        current_auto_approved_count = self.auto_approved_count or 0
        logger.debug(f"Room {self.pk}: Current inventory = {current_inventory}, Current count = {current_count}, Current auto_approved_count = {current_auto_approved_count}")

        # Calculate differences
        count_diff = old_count - current_count if old_count is not None else 0
        auto_approved_diff = old_auto_approved_count - current_auto_approved_count if old_auto_approved_count is not None else 0

        # Check if inventory will be zero after reduction
        will_inventory_be_zero = False
        if count_diff > 0 or auto_approved_diff > 0:
            total_reduction = count_diff + auto_approved_diff
            if total_reduction > 0:
                if current_inventory >= total_reduction:
                    self.inventory = current_inventory - total_reduction
                    logger.info(f"Room {self.pk}: Reduced inventory by {total_reduction} (count_diff={count_diff}, auto_approved_diff={auto_approved_diff}) to {self.inventory}")
                    if self.inventory == 0:
                        will_inventory_be_zero = True
                else:
                    logger.error(f"Room {self.pk}: Cannot reduce inventory by {total_reduction} as it would result in negative inventory")
                    raise ValidationError(_('نمی‌توان موجودی را کاهش داد زیرا کمتر از مجموع کسر رزروها می‌شود.'))

        super().save(*args, **kwargs)

        # Handle inventory reaching zero (either manually or due to count/auto_approved_count reduction)
        if (old_instance and old_inventory != 0 and self.inventory == 0) or will_inventory_be_zero:
            room_name = self.title.strip() if self.title else "اتاق"
            room_full_name = f"{room_name} - آیدی {self.pk}"
            status = "تکمیل"

            logger.info(f"Room {self.pk}: Inventory changed to 0 for '{room_full_name}', attempting to send SMS")
            try:
                from reservation.sms.sms import send_room_availability_sms
                success = send_room_availability_sms(room_full_name, status)
                if success:
                    logger.info(f"Room {self.pk}: SMS sent successfully for '{room_full_name}'")
                else:
                    logger.error(f"Room {self.pk}: Failed to send SMS for '{room_full_name}'")
            except Exception as e:
                logger.error(f"Room {self.pk}: Exception while sending SMS for '{room_full_name}': {str(e)}")







# مدل بازه زمانی اتاق ها 
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
        UserLevel if UserLevel else 'accounts.UserLevel',
        on_delete=models.CASCADE,
        verbose_name=_('سطح کاربری'),
        related_name='room_date_prices',
        help_text=_('قیمت فقط برای این سطح کاربر نمایش داده می‌شود'),
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
        help_text=_('در صورت درصدی بودن، عدد بین 1 تا 100؛ در صورت ثابت بودن، مبلغ به تومان'),
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
            models.CheckConstraint(
                check=models.Q(discount_type='percentage', discount_value__gte=1, discount_value__lte=100) |
                      models.Q(discount_type='fixed', discount_value__gte=0) |
                      models.Q(discount_type='none', discount_value=0),
                name='check_discount_value_validity'
            ),
            models.CheckConstraint(
                check=models.Q(discount_type='fixed', is_fixed_discount_one_time=True) |
                      models.Q(discount_type__in=['none', 'percentage'], is_fixed_discount_one_time=False),
                name='check_fixed_discount_one_time'
            ),
            models.CheckConstraint(
                check=models.Q(discount_type='percentage', discount_date__isnull=False) |
                      models.Q(discount_type='fixed', discount_date__isnull=True) |
                      models.Q(discount_type='none', discount_date__isnull=True),
                name='check_discount_date_required'
            ),
            models.CheckConstraint(
                check=models.Q(discount_date__gte=models.F('start_date'), discount_date__lte=models.F('end_date')) |
                      models.Q(discount_date__isnull=True),
                name='check_discount_date_within_range'
            ),
        ]

    def clean(self):
        """اعتبارسنجی‌های اضافی در سطح مدل"""
        # اعتبارسنجی مقدار تخفیف درصدی
        if self.discount_type == 'percentage' and (self.discount_value < 1 or self.discount_value > 100):
            raise ValidationError(_('مقدار تخفیف درصدی باید بین 1 تا 100 باشد.'))

        # اعتبارسنجی تخفیف ثابت و گزینه اولین خرید
        if self.discount_type == 'fixed' and not self.is_fixed_discount_one_time:
            raise ValidationError(_('برای تخفیف ثابت، باید گزینه "تخفیف اولین خرید" فعال باشد.'))
        if self.discount_type == 'percentage' and self.is_fixed_discount_one_time:
            raise ValidationError(_('گزینه "تخفیف اولین خرید" فقط برای تخفیف ثابت قابل استفاده است.'))

        # اعتبارسنجی تاریخ تخفیف
        if self.discount_type == 'percentage' and not self.discount_date:
            raise ValidationError(_('برای تخفیف درصدی، باید تاریخ انقضای تخفیف مشخص شود.'))
        if self.discount_type == 'fixed' and self.discount_date:
            raise ValidationError(_('برای تخفیف ثابت، نباید تاریخ انقضای تخفیف مشخص شود.'))

        # اعتبارسنجی بازه تاریخ تخفیف
        if self.discount_date:
            if self.discount_date < self.start_date:
                raise ValidationError(_('تاریخ انقضای تخفیف نمی‌تواند قبل از تاریخ شروع بازه باشد.'))
            if self.discount_date > self.end_date:
                raise ValidationError(_('تاریخ انقضای تخفیف نمی‌تواند بعد از تاریخ پایان بازه باشد.'))

    def save(self, *args, **kwargs):
        self.full_clean()  # اجرای اعتبارسنجی‌ها قبل از ذخیره
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.room} | {self.user_level} | {self.start_date} تا {self.end_date}'
    
    
    
    
    
    

#مدل بستن یه روز از بازه خواستی 
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
        help_text=_('اگر انتخاب شود، فقط برای این سطح کاربر غیرفعال است')
    )

    class Meta:
        verbose_name = _('تاریخ بستن بازه')
        verbose_name_plural = _('تاریخ‌های بستن بازه')
        unique_together = ('room_date', 'date', 'user_level')
        ordering = ['date']

    def __str__(self):
        user_level_display = self.user_level if self.user_level else 'همه سطوح'
        return f'{self.room_date} - {self.date} - {user_level_display}'
    
    
    
    


#مدت زمان تایید رزرو 
class ReservationApprovalDuration(models.Model):
    duration_minutes = models.PositiveIntegerField(
        verbose_name=_('مدت زمان تایید رزرو (دقیقه)'),
        help_text=_('مدت زمانی که برای تایید رزرو توسط ادمین اختصاص داده شده است. برحسب دقیقه.'),
        default=5,
    )

    class Meta:
        verbose_name = _('مدت زمان تایید رزرو')
        verbose_name_plural = _('مدت زمان‌های تایید رزرو')

    def __str__(self):
        return f'{self.duration_minutes} دقیقه'
    

    
    
    
#مدل مسافران اشخاص در هتل 
def validate_phone_number(value):
    if not value:
        raise ValidationError(_('شماره موبایل نمی‌تواند خالی باشد.'))
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError(_('شماره موبایل باید ۱۱ رقم باشد و با 09 شروع شود. مثال: 09123456789'))


def validate_identification_code(value):
    if not value:
        raise ValidationError(_('کد شناسایی نمی‌تواند خالی باشد.'))
    if re.match(r'^\d{10}$', value) or re.match(r'^[A-Z0-9]{6,9}$', value):
        return value
    raise ValidationError(_('کد شناسایی نامعتبر است. باید یا کد ملی ۱۰ رقمی باشد یا پاسپورت بین ۶ تا ۹ کاراکتر شامل حروف و اعداد.'))


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
        null=True,  # NULL در دیتابیس مجاز ولی ولیدیتور جلوشو می‌گیره
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
                condition=~Q(identification_code=None),  # شرط فقط برای مقدارهای غیر NULL
                name='unique_user_identification_code'
            )
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.identification_code})'

    def clean(self):
        super().clean()
        
        



# مدل لوگو های هتل در صفحه اصلی 
class BestHotels(models.Model):
    order = models.PositiveIntegerField(
        verbose_name=_("ترتیب"),
        unique=True
    )
    title_logo = models.CharField(
        verbose_name=_("عنوان لوگو"),
        max_length=128
    )
    image_logo_hotel = models.ImageField(
        verbose_name=_("عکس لوگو هتل"),
        upload_to="images/best_hotels/"
    )

    class Meta:
        verbose_name = _("لوگو هتل")
        verbose_name_plural = _("لوگو هتل ها")
        ordering = ['order']

    def __str__(self):
        return f"{self.order} - {self.title_logo}"
    
    



#مدل رزرو های کاربران سایت 
# ---------------- Reservationhotel ----------------
class Reservationhotel(models.Model):
    STATUS_CHOICES = [
        ('paid', _('پرداخت شده')),
        ('unpaid', _('پرداخت نشده')),
        ('confirmed', _('تایید رزرو')),
        ('unconfirmed', _('عدم تایید رزرو')),
        ('cancelled', _('لغو شده')),
    ]

    buyer = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر خریدار'),
        related_name='reservations',
    )
    reserver_first_name = models.CharField(_('نام رزرو کننده'), max_length=256)
    reserver_last_name = models.CharField(_('نام خانوادگی رزرو کننده'), max_length=256)
    reserver_phone_number = models.CharField(_('شماره تماس رزرو کننده'), max_length=11)
    reserver_national_code = models.CharField(_('کد ملی رزرو کننده'), max_length=10, blank=True, null=True)

    check_in_date = jmodels.jDateField(_('تاریخ ورود'))
    check_out_date = jmodels.jDateField(_('تاریخ خروج'))

    total_price = models.DecimalField(_('مجموع قیمت'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    discount = models.DecimalField(_('تخفیف کد تخفیف'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    hotel_fixed_discount = models.DecimalField(_('تخفیف ثابت هتل'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    final_price = models.DecimalField(_('قیمت نهایی'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    half_day_in_charge = models.DecimalField(_('نیم‌شارژ ورود'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    half_day_out_charge = models.DecimalField(_('نیم‌شارژ خروج'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    total_half_day_charge = models.DecimalField(_('مجموع نیم‌شارژها'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    total_extra_passenger_charge = models.DecimalField(_('مجموع قیمت نفرات اضافه'), max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)])

    tracking_code = models.CharField(max_length=20, unique=True, verbose_name='کد پیگیری رزرو')
    additional_notes = models.TextField(_('توضیحات تکمیلی'), blank=True, default='')
    status = models.CharField(_('وضعیت رزرو'), max_length=20, choices=STATUS_CHOICES, default='unpaid')

    created_at = jmodels.jDateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = jmodels.jDateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)

    class Meta:
        verbose_name = _('رزرو')
        verbose_name_plural = _('رزرو ها')

    def __str__(self):
        return f'رزرو {self.tracking_code} توسط {self.buyer.phone_number}'

    @cached_property
    def nights_count(self):
        if self.check_in_date and self.check_out_date:
            check_in = self.check_in_date.togregorian() if isinstance(self.check_in_date, jdatetime.date) else self.check_in_date
            check_out = self.check_out_date.togregorian() if isinstance(self.check_out_date, jdatetime.date) else self.check_out_date
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

    def calculate_total_price(self):
        if not self.pk or not self.reservation_rooms.exists():
            return Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')

        hotel = self.reservation_rooms.first().room.hotel
        if not all(res_room.room.hotel == hotel for res_room in self.reservation_rooms.all()):
            raise ValidationError('تمام اتاق‌ها باید از یک هتل باشند.')

        total = Decimal('0')  # فقط قیمت پایه (بدون نیم‌شارژ و نفر اضافه)
        total_extra = Decimal('0')  # مجموع قیمت نفرات اضافه
        total_discount = Decimal('0')  # تخفیف کل (درصدی + ثابت اتاق + کد تخفیف)
        room_fixed_discount = Decimal('0')  # تخفیف ثابت اتاق‌ها
        half_day_in_charge = Decimal('0')  # نیم‌شارژ ورود
        half_day_out_charge = Decimal('0')  # نیم‌شارژ خروج

        nights = self.nights_count
        if nights <= 0:
            return total, total_extra, total_discount, half_day_in_charge, half_day_out_charge, total, total, total

        user_level = getattr(getattr(self.buyer, 'natural_profile', None), 'level', None)
        check_in_date_std = self.check_in_date.togregorian() if isinstance(self.check_in_date, jdatetime.date) else self.check_in_date

        for res_room in self.reservation_rooms.all():
            room = res_room.room
            quantity = res_room.quantity
            total_guests = res_room.passengers.count()
            base_capacity = room.room_capacity * quantity
            extra_guests = max(0, total_guests - base_capacity)

            price_obj = room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level=user_level
            ).first() or room.date_prices.filter(
                start_date__lte=check_in_date_std,
                end_date__gte=check_in_date_std,
                user_level__isnull=True
            ).first()

            if not price_obj:
                raise ValidationError(f'قیمت برای تاریخ {check_in_date_std} در اتاق {room.title} موجود نیست.')

            daily_price = Decimal(price_obj.price)

            # فقط قیمت پایه برای total
            room_total = daily_price * quantity * nights
            total += room_total

            # قیمت نفرات اضافه
            extra_price_per_person = Decimal(res_room.extra_passenger_price) if res_room.extra_passenger_price else Decimal(price_obj.extra_passenger_price)
            extra_price = extra_price_per_person * extra_guests
            total_extra += extra_price * nights * quantity

            # اعمال نیم‌شارژ (فقط اگر هتل پشتیبانی کند)
            if res_room.half_day_in_selected and hotel.has_check_in_half_day_charge:
                half_day_in_charge += res_room.half_day_in_price
            if res_room.half_day_out_selected and hotel.has_check_out_half_day_charge:
                half_day_out_charge += res_room.half_day_out_price

            # تخفیف‌های RoomDatePrice (درصدی یا ثابت)
            discount = Decimal('0')
            if price_obj.discount_type == 'percentage' and price_obj.discount_date:
                discount_date_std = (
                    price_obj.discount_date.togregorian()
                    if isinstance(price_obj.discount_date, jdatetime.date)
                    else price_obj.discount_date
                )
                if check_in_date_std <= discount_date_std:
                    discount = daily_price * (Decimal(price_obj.discount_value) / Decimal('100')) * quantity * nights
            elif price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
                if not self.buyer.reservations.exclude(pk=self.pk).exists():
                    discount = Decimal(price_obj.discount_value) * quantity

            # اضافه کردن تخفیف ثابت از ReservationRoom
            if res_room.fixed_discount:
                room_fixed_discount += Decimal(res_room.fixed_discount) * nights  # تخفیف ثابت اتاق برای تعداد شب‌ها

            total_discount += discount

        # اضافه کردن تخفیف ثابت اتاق‌ها به کل تخفیف
        total_discount += room_fixed_discount

        # اعمال تخفیف‌های کد تخفیف و تخفیف ثابت هتل
        total_discount += self.discount  # تخفیف کد تخفیف
        total_discount += self.hotel_fixed_discount  # تخفیف ثابت هتل

        total_half_day_charge = half_day_in_charge + half_day_out_charge

        # نهایی: مجموع اتاق + نفر اضافه + نیم‌شارژها - تخفیف
        final_price = total + total_extra + total_half_day_charge - total_discount
        if final_price < 0:
            final_price = Decimal('0')

        return total, total_extra, total_discount, half_day_in_charge, half_day_out_charge, total_half_day_charge, self.discount, final_price

    def save(self, *args, **kwargs):
        if not getattr(self, '_skip_price_calculation', False):
            if not self.pk or any(getattr(self, field) is None for field in [
                'total_price', 'discount', 'hotel_fixed_discount', 'final_price',
                'half_day_in_charge', 'half_day_out_charge', 'total_half_day_charge',
                'total_extra_passenger_charge'
            ]):
                total, total_extra, total_discount, half_in, half_out, total_half, code_discount, final = self.calculate_total_price()
                self.total_price = total
                self.discount = code_discount
                self.hotel_fixed_discount = self.hotel_fixed_discount or Decimal('0')  # اطمینان از مقدار ثابت هتل
                self.half_day_in_charge = half_in
                self.half_day_out_charge = half_out
                self.total_half_day_charge = total_half
                self.total_extra_passenger_charge = total_extra
                self.final_price = final
        super().save(*args, **kwargs)


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
        help_text='قیمت هر نفر اضافه (قابل تغییر؛ پیش‌فرض از RoomDatePrice گرفته می‌شود)'
    )
    fixed_discount = models.DecimalField(
        'تخفیف ثابت',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        default=Decimal('0'),
        blank=True,
        null=True,
        help_text='تخفیف ثابت برای این اتاق (از RoomDatePrice گرفته می‌شود)'
    )
    subtotal = models.PositiveBigIntegerField(
        verbose_name='مجموع قیمت (تومان)',
        null=False,
        blank=False,
        default=0
    )
    primary_passengers_count = models.PositiveIntegerField(
        default=1,
        verbose_name='تعداد نفر اصلی'
    )
    extra_passengers_count = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد نفر اضافه'
    )
    half_day_in_selected = models.BooleanField(default=False, verbose_name='نیم‌شارژ ورود فعال است؟')
    half_day_out_selected = models.BooleanField(default=False, verbose_name='نیم‌شارژ خروج فعال است؟')
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

    def calculate_half_day_prices(self):
        if not self.room_id:
            self.half_day_in_price = Decimal('0')
            self.half_day_out_price = Decimal('0')
            return

        hotel = self.room.hotel
        half_in = Decimal('0')
        half_out = Decimal('0')

        if self.half_day_in_selected and getattr(hotel, 'has_check_in_half_day_charge', False):
            half_in = (self.price_per_night / Decimal('2')) * self.quantity
        if self.half_day_out_selected and getattr(hotel, 'has_check_out_half_day_charge', False):
            half_out = (self.price_per_night / Decimal('2')) * self.quantity

        self.half_day_in_price = half_in
        self.half_day_out_price = half_out

    def calculate_room_prices(self):
        if not self.room_id or not self.reservation_id:
            self.price_per_night = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        nights = self.reservation.nights_count
        if nights <= 0:
            self.price_per_night = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        check_in_date_std = (
            self.reservation.check_in_date.togregorian()
            if isinstance(self.reservation.check_in_date, jdatetime.date)
            else self.reservation.check_in_date
        )
        user_level = getattr(getattr(self.reservation.buyer, 'natural_profile', None), 'level', None)

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
            self.price_per_night = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        self.price_per_night = Decimal(price_obj.price)
        self.fixed_discount = Decimal('0')

        if price_obj.discount_type != 'none':
            if price_obj.discount_type == 'percentage' and price_obj.discount_date:
                discount_date_std = (
                    price_obj.discount_date.togregorian()
                    if isinstance(price_obj.discount_date, jdatetime.date)
                    else price_obj.discount_date
                )
                if check_in_date_std <= discount_date_std:
                    discount_percentage = Decimal(price_obj.discount_value) / Decimal('100')
                    self.price_per_night = self.price_per_night * (1 - discount_percentage)
            elif price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
                self.fixed_discount = Decimal(price_obj.discount_value) * self.quantity

        room_total = (self.price_per_night * self.quantity * nights) + self.half_day_in_price + self.half_day_out_price
        room_total -= self.fixed_discount
        self.subtotal = int(room_total.quantize(Decimal('1'), rounding=ROUND_UP))

    def assign_passenger_types(self):
        if not self.pk:
            return

        passengers_list = list(self.passengers.all().order_by('pk'))
        total_passengers = len(passengers_list)

        if total_passengers == 0:
            return

        if total_passengers >= 1:
            passengers_list[0].passenger_type = 'primary'
            passengers_list[0].save(update_fields=['passenger_type'])

        if total_passengers >= 2:
            passengers_list[1].passenger_type = 'secondary'
            passengers_list[1].save(update_fields=['passenger_type'])

        if total_passengers > 2:
            passengers_list[-1].passenger_type = 'extra'
            passengers_list[-1].save(update_fields=['passenger_type'])

        for i in range(2, total_passengers - 1):
            if i < total_passengers and passengers_list[i].passenger_type not in ['primary', 'extra']:
                passengers_list[i].passenger_type = 'secondary'
                passengers_list[i].save(update_fields=['passenger_type'])

    def save(self, *args, **kwargs):
        if not self.extra_passenger_price and self.room:
            check_in_date_std = (
                self.reservation.check_in_date.togregorian()
                if isinstance(self.reservation.check_in_date, jdatetime.date)
                else self.reservation.check_in_date
            )
            user_level = getattr(getattr(self.reservation.buyer, 'natural_profile', None), 'level', None)
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

        self.calculate_half_day_prices()
        self.calculate_room_prices()
        super().save(*args, **kwargs)

        if getattr(self, '_assign_passenger_types', False) and self.passengers.exists():
            self.assign_passenger_types()
            
            

# ---------------- ReservationRoomPassenger ----------------
def validate_national_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد')

    check_digits = int(value[9])
    total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11

    if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
        raise ValidationError('کد ملی معتبر نیست')

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
        constraints = [
            models.UniqueConstraint(
                fields=['reservation_room', 'national_code'],
                name='unique_national_code_per_room'
            )
        ]

    def clean(self):
        # الزامی بودن فیلدها برای مسافر اصلی
        if self.passenger_type == 'primary':
            missing_fields = []
            for field_name in ['first_name', 'last_name', 'mobile_number', 'national_code']:
                if not getattr(self, field_name):
                    missing_fields.append(field_name)
            if missing_fields:
                raise ValidationError(f'برای مسافر اصلی، فیلدهای {missing_fields} الزامی هستند.')

        # یکتایی کد ملی در همان اتاق
        if self.national_code:
            qs = ReservationRoomPassenger.objects.filter(
                reservation_room=self.reservation_room,
                national_code=self.national_code
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('کد ملی باید برای هر مسافر در همان اتاق یکتا باشد.')

    def save(self, *args, **kwargs):
        self.is_primary = self.passenger_type == 'primary'
        self.full_clean()  # اجرای تمام اعتبارسنجی‌ها قبل از ذخیره
        super().save(*args, **kwargs)

        # فراخوانی assign_passenger_types فقط اگر به صراحت درخواست شده (از ادمین یا API)
        if getattr(self.reservation_room, '_assign_passenger_types', False) and self.reservation_room:
            self.reservation_room.assign_passenger_types()

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.get_passenger_type_display()})'