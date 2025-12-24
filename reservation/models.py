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
from config.models import UserLevel  # 👈 



# 🌐 Django
from django.db import models , transaction
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
from bashgah_moshtarian.sms.sms import send_customer_club_sms, send_customer_club_deduct_sms
from config.models import UserLevel
from finance.models import Wallet
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




#مدل امکانات رفاهی و تفریحی هتل 
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
    is_draft = models.BooleanField(
        default=True,
        verbose_name=_('پیش‌نویس'),
        help_text=_('اگر فعال باشد، هتل نمایش داده نمی‌شود. اگر غیرفعال باشد، نمایش داده می‌شود.'),
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_('منتشر شده'),
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
        """بررسی می‌کند که آیا هتل بازه زمانی فعالی برای اتاق‌هایش دارد یا خیر."""
        today = date2jalali(timezone.now().date())
        return self.rooms.filter(
            date_prices__start_date__lte=today,
            date_prices__end_date__gte=today
        ).exists()


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

    class Meta:
        verbose_name = 'تصویر گالری'
        verbose_name_plural = 'تصاویر گالری'
        ordering = ['-id']  # ترتیب بر اساس جدیدترین (یا هر ترتیب دیگه‌ای)

    def __str__(self):
        return f'تصویر گالری {self.gallery.title}'






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
        verbose_name=_('ظرفیت رزرو نیازمند تأیید ادمین'),
        help_text=_('ظرفیت رزروهایی که باید تأیید ادمین داشته باشند'),
        default=0,
        null=True,
        blank=True,
    )
    auto_approved_count = models.PositiveIntegerField(
        verbose_name=_('ظرفیت رزرو بدون تأیید ادمین'),
        help_text=_('ظرفیت رزروهایی که بدون تأیید ادمین تأیید می‌شوند'),
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
        default=0,
    )
    extra_capacity = models.PositiveIntegerField(
        verbose_name=_('ظرفیت نفر اضافه'),
        help_text=_('تعداد نفرات اضافی مجاز'),
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
        help_text=_('تصویر نمایشی اتاق — اختیاری')
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
        
        # بررسی اینکه count و auto_approved_count بیشتر از inventory نباشند
        if current_count > current_inventory:
            raise ValidationError(_(f'ظرفیت رزرو نیازمند تأیید ادمین ({current_count}) نمی‌تواند بیشتر از موجودی فعلی ({current_inventory}) باشد.'))
        if current_auto_approved_count > current_inventory:
            raise ValidationError(_(f'ظرفیت رزرو بدون تأیید ادمین ({current_auto_approved_count}) نمی‌تواند بیشتر از موجودی فعلی ({current_inventory}) باشد.'))

    def __str__(self):
        return f'{self.title} - {self.hotel}' if self.hotel else self.title or 'اتاق بدون نام'

    def save(self, *args, **kwargs):
        # اگر count و auto_approved_count هر دو صفر باشند، inventory هم صفر می‌شود
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
        logger.info(f"Adjusting inventory for Room {self.pk} | quantity={quantity} | auto_approval={auto_approval}")
        if quantity <= 0:
            raise ValidationError(_('تعداد رزرو باید بیشتر از صفر باشد.'))

        with transaction.atomic():
            # قفل کردن رکورد برای جلوگیری از race condition
            room = Room.objects.select_for_update().get(pk=self.pk)
            if auto_approval:
                if room.auto_approved_count < quantity:
                    raise ValidationError(_('ظرفیت بدون تأیید ادمین کافی نیست.'))
                room.auto_approved_count -= quantity
            else:
                if room.count < quantity:
                    raise ValidationError(_('ظرفیت نیازمند تأیید ادمین کافی نیست.'))
                room.count -= quantity
            
            # کاهش موجودی
            old_inventory = room.inventory
            room.inventory -= quantity
            
            room.save(update_fields=['inventory', 'count', 'auto_approved_count'])
            
            # ارسال SMS اگر موجودی صفر شد
            if old_inventory > 0 and room.inventory == 0:
                logger.info(f"Room {room.pk} inventory reached zero. Sending SMS to admins.")
                try:
                    send_room_availability_sms(
                        room_name=f"{room.title} (ID: {room.pk})",
                        status="صفر شد",
                        hotel_name=room.hotel.title if room.hotel else "نامشخص"
                    )
                except Exception as e:
                    logger.error(f"Failed to send SMS for room {room.pk}: {str(e)}")
        
        logger.info(f"Room {self.pk}: Reservation added successfully")

    def revert_inventory_for_cancellation(self, quantity: int, auto_approval: bool):
        logger.info(f"Reverting inventory for Room {self.pk} | quantity={quantity} | auto_approval={auto_approval}")
        if quantity <= 0:
            raise ValidationError(_('تعداد رزرو باید بیشتر از صفر باشد.'))

        with transaction.atomic():
            # قفل کردن رکورد
            room = Room.objects.select_for_update().get(pk=self.pk)
            if auto_approval:
                room.auto_approved_count += quantity
            else:
                room.count += quantity
            room.inventory += quantity
            room.save(update_fields=['inventory', 'count', 'auto_approved_count'])
        logger.info(f"Room {self.pk}: Reservation cancelled and reverted successfully")

    def _send_inventory_sms_if_zero(self):
        """ارسال SMS وقتی موجودی صفر می‌شود - این متد دیگر استفاده نمی‌شود"""
        pass
    
    

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
    UserLevel,
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

    # کد ملی ۱۰ رقمی
    if re.match(r'^\d{10}$', value):
        return value

    # پاسپورت: طول بین 6 تا 9 و باید یا تمام عدد باشد یا حروف در ابتدای رشته و سپس اعداد
    if 6 <= len(value) <= 9 and re.match(r'^[A-Za-z]*\d+$', value):
        return value

    raise ValidationError(_('کد شناسایی نامعتبر است. باید کد ملی ۱۰ رقمی یا شماره پاسپورت بین ۶ تا ۹ کاراکتر باشد (در صورت وجود حروف، حروف باید در ابتدای رشته قرار گیرند).'))


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
    
    



#مدل رزرو های کاربران سایت 
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

    # --- فیلدهای جدید کنسلی ---
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

    

    created_at = jmodels.jDateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = jmodels.jDateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)


    class Meta:
        verbose_name = _('رزرو')
        verbose_name_plural = _('رزرو‌ها')

    def __str__(self):
        return f'رزرو {self.tracking_code} توسط {self.buyer.phone_number}'

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
        # این تابع به ReservationRoom نیاز دارد
        # اگر ReservationRoom در فایل جداگانه است، باید در آن فایل رابطه را تعریف کنید
        # اینجا فرض می‌کنیم که related_name به درستی ست شده است
        if not hasattr(self, 'reservation_rooms'):
            return 0
        return self.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0

    @cached_property
    def total_guests(self):
        total = 0
        if hasattr(self, 'reservation_rooms'):
            for res_room in self.reservation_rooms.all():
                # این هم به مدل Room و ReservationRoomPassenger نیاز دارد
                if res_room.room:
                    total += (res_room.room.room_capacity + res_room.room.extra_capacity) * res_room.quantity
        return total

    def get_hotel(self):
        # این به مدل Room و Hotel نیاز دارد
        if hasattr(self, 'reservation_rooms') and self.reservation_rooms.exists():
            return self.reservation_rooms.first().room.hotel
        return None

    def calculate_cancellation_refund(self):
        hotel = self.get_hotel()
        # این به مدل Hotel.cancellation_penalty نیاز دارد
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

    # --- محاسبه قیمت (همون قبلی) ---
    def calculate_total_price(self):
        # این متد باید قیمت نهایی را با در نظر گرفتن wallet_withdrawal_amount فعلی محاسبه کند.
        # وقتی API View این را صدا می‌زند، wallet_withdrawal_amount از قبل آپدیت شده است.
        if not self.pk or not self.reservation_rooms.exists():
            # برمی‌گرداند (total, total_extra, self.discount, half_in, half_out, total_half, code_discount, final, room_fixed)
            return (Decimal('0'),) * 9 

        # فرض بر این است که ReservationRoom و Room در دسترس هستند
        # باید مطمئن شوید که همه Room‌ها از یک Hotel هستند
        first_res_room = self.reservation_rooms.first()
        if not first_res_room:
            return (Decimal('0'),) * 9

        hotel = first_res_room.room.hotel
        if not all(res_room.room.hotel == hotel for res_room in self.reservation_rooms.all()):
            raise ValidationError('تمام اتاق‌ها باید از یک هتل باشند.')

        total = Decimal('0') # مجموع قیمت اتاق‌ها بدون تخفیف و نفرات اضافه
        total_extra = Decimal('0') # مجموع قیمت نفرات اضافه
        room_fixed_discount = Decimal('0') # تخفیف ثابت اعمال شده روی اتاق
        half_day_in_charge = Decimal('0')
        half_day_out_charge = Decimal('0')

        nights = self.nights_count
        if nights <= 0:
            return (total, total_extra, self.discount, half_day_in_charge, half_day_out_charge, Decimal('0'), self.discount, self.final_price, room_fixed_discount)

        user_level = getattr(getattr(self.buyer, 'natural_profile', None), 'level', None)
        check_in_date_std = self.check_in_date.togregorian() if hasattr(self.check_in_date, 'togregorian') else self.check_in_date

        for res_room in self.reservation_rooms.all():
            room = res_room.room
            quantity = res_room.quantity
            
            # این به ReservationRoomPassenger نیاز دارد
            extra_guests = res_room.passengers.filter(passenger_type='extra').count()

            # این به RoomDatePrice نیاز دارد
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

            # Check if discount_date is available and relevant for fixed discount
            if price_obj and price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
                # Ensure discount_date is not null before comparison
                if price_obj.discount_date and check_in_date_std <= price_obj.discount_date:
                    room_fixed_discount += Decimal(price_obj.discount_value) * quantity
                # If discount_date is null, assume it's always valid if one-time and fixed
                elif not price_obj.discount_date:
                     room_fixed_discount += Decimal(price_obj.discount_value) * quantity

            # فرض بر این است که half_day_in_selected, half_day_out_selected, half_day_in_price, half_day_out_price
            # روی مدل ReservationRoom و has_check_in_half_day_charge, has_check_out_half_day_charge روی مدل Hotel هستند.
            if hasattr(res_room, 'half_day_in_selected') and res_room.half_day_in_selected and hasattr(hotel, 'has_check_in_half_day_charge') and hotel.has_check_in_half_day_charge:
                half_day_in_charge += (res_room.half_day_in_price if hasattr(res_room, 'half_day_in_price') else Decimal('0')) * quantity
            if hasattr(res_room, 'half_day_out_selected') and res_room.half_day_out_selected and hasattr(hotel, 'has_check_out_half_day_charge') and hotel.has_check_out_half_day_charge:
                half_day_out_charge += (res_room.half_day_out_price if hasattr(res_room, 'half_day_out_price') else Decimal('0')) * quantity

        total_half_day_charge = half_day_in_charge + half_day_out_charge
        
        # calculate_total_price باید مقدار تخفیف کد تخفیف را از روی فیلد discount رزرو بخواند، نه از جایی دیگر
        # این فیلد discount توسط کد تخفیف پر شده است.
        # base_price_after_all_discounts_except_wallet: قیمت پس از اعمال همه تخفیف‌ها (کد تخفیف و ثابت اتاق)
        base_price_after_all_discounts_except_wallet = total + total_extra + total_half_day_charge - self.discount - room_fixed_discount
        
        # قیمت نهایی که کاربر باید پرداخت کند = (قیمت پایه - تخفیف‌ها) - مبلغ برداشت از کیف پول
        final_price_to_pay = base_price_after_all_discounts_except_wallet - self.wallet_withdrawal_amount
        
        if final_price_to_pay < 0:
            final_price_to_pay = Decimal('0')

        return (total, total_extra, self.discount, half_day_in_charge, half_day_out_charge,
                total_half_day_charge, self.discount, final_price_to_pay, room_fixed_discount)


    def save(self, *args, **kwargs):
        # این فلگ به ما اجازه می‌دهد تا در برخی موارد (مثل API View) از محاسبه مجدد قیمت جلوگیری کنیم.
        if not getattr(self, '_skip_price_calculation_on_save', False):
            # calculate_total_price باید تمام مقادیر را برگرداند تا اینجا پر شوند
            total, total_extra, code_discount, half_in, half_out, total_half, _, final, room_fixed = self.calculate_total_price()
            self.total_price = total
            self.total_extra_passenger_charge = total_extra
            self.discount = code_discount # مقدار code_discount از calculate_total_price می آید
            self.room_fixed_discount = room_fixed
            self.half_day_in_charge = half_in
            self.half_day_out_charge = half_out
            self.total_half_day_charge = total_half
            self.final_price = final # این final_price شامل کسر wallet_withdrawal_amount است

        super().save(*args, **kwargs)
        
        

# --- متد جدید برای پردازش کد تخفیف ---
def process_discount_after_payment_v2(self):
    """پردازش کد تخفیف با استفاده از متد consume_discount_for_user موجود"""
    if not (self.payment_status == 'paid' and self.applied_discount_code and not self.discount_processed):
        logger.info(f"شرایط اولیه برای پردازش کد تخفیف برقرار نیست: "
                   f"payment_status={self.payment_status}, "
                   f"applied_discount_code={self.applied_discount_code}, "
                   f"discount_processed={self.discount_processed}")
        return False

    try:
        from django.db import transaction

        # ابتدا وضعیت فعلی را دیباگ کنیم
        logger.info(f"🔍 شروع پردازش کد تخفیف برای رزرو {self.tracking_code}")
        self._debug_discount_status()

        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().get(pk=self.pk)
            if reservation.discount_processed:
                logger.info(f"کد تخفیف برای رزرو {reservation.tracking_code} قبلاً پردازش شده است")
                return True

            # پیدا کردن کد تخفیف (Room / Hotel / Personal)
            discount_obj, discount_type = find_discount_obj_by_code(reservation.applied_discount_code)
            if not discount_obj:
                logger.error(f"❌ کد تخفیف {reservation.applied_discount_code} یافت نشد")
                return False
            logger.info(f"✅ کد تخفیف پیدا شد: type={discount_type} code={discount_obj.code}")

            # دیباگ وضعیت کد تخفیف قبل از مصرف
            logger.info(f"🟡 وضعیت کد تخفیف قبل از مصرف:")
            logger.info(f"   - کد: {discount_obj.code}")
            logger.info(f"   - remaining_uses: {discount_obj.remaining_uses}")
            logger.info(f"   - usage_limit: {discount_obj.usage_limit}")
            logger.info(f"   - کاربر در activated_users: {reservation.buyer in discount_obj.activated_users.all()}")

            # برای کدهای شخصی از متد apply_use استفاده کن و فیلدهای رزرو را ست کن
            try:
                if discount_type == 'personal':
                    logger.info(f"🔍 پردازش کد شخصی {discount_obj.code} برای رزرو {reservation.tracking_code}")
                    if discount_obj.user_id != reservation.buyer_id:
                        logger.warning(f"کد شخصی {discount_obj.code} متعلق به کاربر دیگری است")
                        return False

                    # استفاده اتمیک از متد apply_use
                    try:
                        success = discount_obj.apply_use(reservation.buyer)
                    except ValueError as e:
                        logger.warning(f"کد شخصی {discount_obj.code} قابل استفاده نیست: {e}")
                        return False

                    if success:
                        reservation.personal_discount_code = discount_obj
                        reservation.personal_discount_used = True
                        reservation.discount_processed = True
                        reservation.save(update_fields=['personal_discount_code', 'personal_discount_used', 'discount_processed'])
                        logger.info(f"🟢 کد شخصی {discount_obj.code} برای رزرو {reservation.tracking_code} مصرف شد")
                        return True
                    else:
                        logger.error(f"❌ apply_use برای کد شخصی {discount_obj.code} False برگرداند")
                        return False

                # استفاده از متد consume_discount_for_user برای انواع room/hotel
                success = discount_obj.consume_discount_for_user(reservation.buyer)
                if success:
                    reservation.discount_processed = True
                    reservation.save(update_fields=['discount_processed'])
                    
                    # رفرش کردن discount_obj برای گرفتن مقادیر جدید
                    discount_obj.refresh_from_db()
                    
                    # دیباگ وضعیت بعد از مصرف
                    logger.info(f"🟢 وضعیت کد تخفیف بعد از مصرف:")
                    logger.info(f"   - کد: {discount_obj.code}")
                    logger.info(f"   - remaining_uses: {getattr(discount_obj, 'remaining_uses', None)}")
                    if hasattr(discount_obj, 'activated_users'):
                        in_activated = reservation.buyer in discount_obj.activated_users.all()
                    else:
                        in_activated = False
                    logger.info(f"   - کاربر در activated_users: {in_activated}")
                    logger.info(f"   - discount_processed: {reservation.discount_processed}")
                    
                    logger.info(f"✅ کد تخفیف با موفقیت مصرف شد برای رزرو {reservation.tracking_code}")
                    return True
                else:
                    logger.error(f"❌ متد consume_discount_for_user False برگرداند")
                    return False

            except ValueError as e:
                logger.error(f"❌ خطا در مصرف کد تخفیف (ValueError): {e}")
                return False
            except Exception as e:
                logger.error(f"❌ خطای غیرمنتظره در مصرف کد تخفیف: {e}")
                import traceback
                logger.error(f"❌ جزئیات خطا: {traceback.format_exc()}")
                return False

    except Exception as e:
        logger.error(f"🔴 خطا در پردازش کد تخفیف: {e}")
        import traceback
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")
        return False

def _debug_discount_status(self):
    """تابع کمکی برای دیباگ وضعیت کد تخفیف"""
    try:
        discount_obj, discount_type = find_discount_obj_by_code(self.applied_discount_code)
        if not discount_obj:
            logger.error(f"🔴 کد تخفیف {self.applied_discount_code} در دیباگ یافت نشد")
            return

        logger.info(f"🔍 دیباگ کد تخفیف {discount_obj.code} (نوع: {discount_type}):")
        # common attributes
        logger.info(f"   - discount_processed در رزرو: {self.discount_processed}")
        # type-specific
        if discount_type in ('room', 'hotel'):
            logger.info(f"   - remaining_uses: {discount_obj.remaining_uses}")
            logger.info(f"   - usage_limit: {discount_obj.usage_limit}")
            logger.info(f"   - کاربر در activated_users: {self.buyer in discount_obj.activated_users.all()}")
            logger.info(f"   - required_points: {discount_obj.required_points}")
        else:
            # personal
            logger.info(f"   - uses_count: {getattr(discount_obj, 'uses_count', None)}")
            logger.info(f"   - usage_limit: {getattr(discount_obj, 'usage_limit', None)}")
        if getattr(discount_obj, 'expires_at', None):
            logger.info(f"   - expires_at: {discount_obj.expires_at}")
    except Exception as e:
        logger.error(f"🔴 خطا در دیباگ کد تخفیف: {e}")


def find_discount_obj_by_code(code):
    """Return (obj, type) where type is 'room'|'hotel'|'personal' or (None, None) if not found."""
    try:
        obj = RoomDiscountCode.objects.get(code__iexact=code)
        return obj, 'room'
    except RoomDiscountCode.DoesNotExist:
        pass

    try:
        obj = HotelDiscountCode.objects.get(code__iexact=code)
        return obj, 'hotel'
    except HotelDiscountCode.DoesNotExist:
        pass

    try:
        obj = PersonalDiscountCode.objects.get(code__iexact=code)
        return obj, 'personal'
    except PersonalDiscountCode.DoesNotExist:
        pass

    return None, None
        
        
        
_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)

@receiver(post_save, sender=Reservationhotel)
def notify_status_change_and_assign_points(sender, instance, created, **kwargs):
    try:
        if get_skip_points_and_sms():
            logger.info(f"اجرای سیگنال برای رزرو {instance.tracking_code} نادیده گرفته شد.")
            return

        channel_layer = get_channel_layer()
        cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
        cache_key_points = f"points_assignment_lock_{instance.tracking_code}"
        cache_key_discount = f"discount_process_lock_{instance.tracking_code}"
        timer = None

        if cache.get(cache_key_points) or cache.get(cache_key_discount):
            logger.info(f"Processing skipped for {instance.tracking_code} due to lock (points or discount)")
            return

        # Additional safeguard: if payment completed and applied code is a personal code
        # but reservation.personal_discount_used is still False, try to mark it now.
        # This ensures that if another signal/path consumed the PersonalDiscountCode
        # but did not update the reservation, we still mark the reservation as used.
        if instance.payment_status == 'paid' and instance.applied_discount_code and not instance.personal_discount_used:
            try:
                with transaction.atomic():
                    # get fresh reservation row
                    reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                    # re-check under lock
                    if reservation.personal_discount_used:
                        logger.debug(f"personal_discount_used already set for {reservation.tracking_code}")
                    else:
                        try:
                            pd = PersonalDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                        except PersonalDiscountCode.DoesNotExist:
                            pd = None

                        if pd:
                            if pd.user_id != reservation.buyer_id:
                                logger.warning(f"Personal code {pd.code} does not belong to buyer for reservation {reservation.tracking_code}")
                            else:
                                # try to increment uses_count if possible
                                if pd.uses_count < pd.usage_limit:
                                    pd.uses_count += 1
                                    pd.save(update_fields=['uses_count'])
                                    logger.info(f"Incremented uses_count for personal code {pd.code} -> {pd.uses_count}")
                                else:
                                    logger.warning(f"Personal code {pd.code} already at usage limit ({pd.uses_count}/{pd.usage_limit})")

                                reservation.personal_discount_code = pd
                                reservation.personal_discount_used = True
                                reservation.discount_processed = True
                                reservation.save(update_fields=['personal_discount_code', 'personal_discount_used', 'discount_processed'])
                                logger.info(f"Marked reservation {reservation.tracking_code} as using personal code {pd.code}")

            except Exception as e:
                logger.error(f"Error while marking personal discount for reservation {instance.tracking_code}: {e}")

        if instance.capacity_status == 'rejected':
            rooms = ReservationRoom.objects.filter(reservation=instance).select_related('room')
            with transaction.atomic():
                for r in rooms:
                    room = Room.objects.select_for_update().get(pk=r.room.pk)
                    room.revert_inventory_for_cancellation(r.quantity, getattr(r, 'was_auto_approved', False))
            cache.delete_many([cache_key_approval, cache_key_payment, cache_key_discount])
            timer = 0
            logger.debug(f"رزرو {instance.tracking_code} رد شد، تایمرها حذف شدند.")

        elif instance.payment_status == 'paid' and not instance.points_assigned:
            logger.info(f"وضعیت پرداخت برای رزرو {instance.tracking_code} به 'paid' تغییر کرد. بررسی تخصیص امتیاز...")
            with transaction.atomic():
                reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                if reservation.points_assigned:
                    logger.info(f"Points already assigned for {reservation.tracking_code}, skipping.")
                    return

                cache.set(cache_key_points, True, timeout=60)

                total_points = 0
                for res_room in reservation.reservation_rooms.select_related('room').all():
                    room = res_room.room
                    quantity = res_room.quantity
                    points = room.customer_club_points or 0
                    total_points += points * quantity

                if total_points > 0:
                    customer_points, created = CustomerClubPoint.objects.get_or_create(
                        user=reservation.buyer,
                        defaults={'points': 0}
                    )
                    customer_points.points += total_points
                    set_skip_points_and_sms(True)
                    customer_points.save()
                    set_skip_points_and_sms(False)
                    logger.info(f"امتیازهای باشگاه مشتریان ({total_points}) به کاربر {reservation.buyer.phone_number} برای رزرو {reservation.tracking_code} اضافه شد.")

                    reservation.points_assigned = True
                    reservation.save(update_fields=['points_assigned'])

                    send_customer_club_sms(
                        phone_number=reservation.buyer.phone_number,
                        user_name=reservation.buyer.first_name or reservation.buyer.phone_number,
                        added_points=total_points,
                        current_points=customer_points.points
                    )
                else:
                    logger.info(f"هیچ امتیازی برای رزرو {instance.tracking_code} تخصیص داده نشد (total_points=0).")
                    reservation.points_assigned = True
                    reservation.save(update_fields=['points_assigned'])

                # اضافه کردن مبلغ پرداخت شده به total_purchase پروفایل کاربر
                try:
                    if hasattr(reservation.buyer, 'natural_profile') and reservation.buyer.natural_profile:
                        profile = reservation.buyer.natural_profile
                        total_paid = reservation.final_price or 0
                        if total_paid > 0:
                            profile.total_purchase += total_paid
                            profile.save(update_fields=['total_purchase'])
                            logger.info(f"مجموع خرید کاربر {reservation.buyer.phone_number} به مبلغ {total_paid} تومان افزایش یافت. مجموع فعلی: {profile.total_purchase}")
                            # آپدیت سطح کاربری بر اساس مجموع خرید جدید
                            profile.update_level()
                except Exception as e:
                    logger.error(f"خطا در آپدیت total_purchase برای کاربر {reservation.buyer.phone_number}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

                cache.delete(cache_key_points)

        elif instance.payment_status == 'paid' and instance.applied_discount_code and not instance.discount_processed:
            logger.info(f"پردازش کد تخفیف برای رزرو {instance.tracking_code} در حال انجام است...")
            with transaction.atomic():
                reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                if reservation.discount_processed:
                    logger.info(f"Discount already processed for {reservation.tracking_code}, skipping.")
                    return

                cache.set(cache_key_discount, True, timeout=60)

                discount_obj, discount_type = find_discount_obj_by_code(reservation.applied_discount_code)
                if not discount_obj:
                    logger.error(f"کد تخفیف {reservation.applied_discount_code} برای رزرو {reservation.tracking_code} یافت نشد")
                    cache.delete(cache_key_discount)
                    return
                logger.debug(f"کد تخفیف پیدا شد: type={discount_type}, code={reservation.applied_discount_code}")

                # expire check (works for Room/Hotel/Personal if field exists)
                if getattr(discount_obj, 'expires_at', None) and discount_obj.expires_at < jdatetime.datetime.now().date():
                    logger.warning(f"کد تخفیف {discount_obj.code} برای رزرو {reservation.tracking_code} منقضی شده است")
                    cache.delete(cache_key_discount)
                    return

                if discount_type in ('room', 'hotel'):
                    if discount_obj.users.exists() and reservation.buyer not in discount_obj.users.all():
                        logger.warning(f"کاربر {reservation.buyer.phone_number} مجاز به استفاده از کد تخفیف {discount_obj.code} نیست")
                        cache.delete(cache_key_discount)
                        return

                    user_level = getattr(getattr(reservation.buyer, 'natural_profile', None), 'level', None)
                    if discount_obj.user_level and discount_obj.user_level != user_level:
                        logger.warning(f"سطح کاربری {user_level} برای کد تخفیف {discount_obj.code} معتبر نیست")
                        cache.delete(cache_key_discount)
                        return

                    if discount_obj.remaining_uses <= 0:
                        logger.warning(f"دفعات استفاده از کد تخفیف {discount_obj.code} به پایان رسیده است")
                        cache.delete(cache_key_discount)
                        return

                    if reservation.buyer in discount_obj.activated_users.all():
                        logger.warning(f"کاربر {reservation.buyer.phone_number} قبلاً از کد تخفیف {discount_obj.code} استفاده کرده است")
                        cache.delete(cache_key_discount)
                        return

                    activation_filter = {
                        'user': reservation.buyer,
                        'discount_type': discount_type,
                        **({'room_discount_code': discount_obj} if discount_type == 'room' else {'hotel_discount_code': discount_obj}),
                    }
                    activation_record = DiscountActivationRecord.objects.filter(**activation_filter).first()
                    if not activation_record:
                        logger.error(f"رکورد فعال‌سازی برای کد تخفیف {discount_obj.code} و کاربر {reservation.buyer.phone_number} یافت نشد")
                        cache.delete(cache_key_discount)
                        return

                    if activation_record.reward_claimed:
                        logger.warning(f"رکورد فعال‌سازی برای کد تخفیف {discount_obj.code} قبلاً استفاده شده است")
                        cache.delete(cache_key_discount)
                        return

                    logger.debug(f"Applying discount {discount_obj.code} for user {reservation.buyer.phone_number}, remaining_uses before: {discount_obj.remaining_uses}")
                    discount_obj.remaining_uses -= 1
                    discount_obj.activated_users.add(reservation.buyer)
                    discount_obj.save()
                    activation_record.reward_claimed = True
                    activation_record.save()
                    reservation.discount_processed = True
                    reservation.save(update_fields=['discount_processed'])
                    logger.debug(f"Discount {discount_obj.code} applied, remaining_uses after: {discount_obj.remaining_uses}")

                    cache.delete(cache_key_discount)
                else:
                    # personal discount: owner-only, no activation record, decrement uses_count atomically
                    logger.debug(f"پردازش کد شخصی برای رزرو {reservation.tracking_code}: owner_id={discount_obj.user_id}, buyer_id={reservation.buyer_id}")
                    if discount_obj.user_id != reservation.buyer_id:
                        logger.warning(f"کد شخصی {discount_obj.code} متعلق به کاربر {discount_obj.user_id} است و کاربر {reservation.buyer_id} مجاز نیست")
                        cache.delete(cache_key_discount)
                        return

                    logger.debug(f"استعلام استفاده کنونی: uses_count={getattr(discount_obj, 'uses_count', None)}, usage_limit={getattr(discount_obj, 'usage_limit', None)}")

                    # اتمیک تلاش برای افزایش uses_count؛ اگر قبلاً توسط مسیر دیگری افزایش یافته بود
                    # و به حد استفاده رسیده بود، ما باز هم رزرو را علامت‌گذاری می‌کنیم اما از افزایش مجدد خودداری می‌کنیم.
                    try:
                        with transaction.atomic():
                            pd = PersonalDiscountCode.objects.select_for_update().get(pk=discount_obj.pk)
                            logger.debug(f"پس از select_for_update: pd.uses_count={pd.uses_count}, pd.usage_limit={pd.usage_limit}")
                            if pd.uses_count < pd.usage_limit:
                                pd.uses_count += 1
                                pd.save(update_fields=['uses_count'])
                                logger.info(f"uses_count کد شخصی {pd.code} افزایش یافت -> {pd.uses_count}")
                            else:
                                logger.warning(f"uses_count کد شخصی {pd.code} قبلاً به حد نهایی رسیده ({pd.uses_count}/{pd.usage_limit}) — افزایش نادیده گرفته شد")

                            # حتی اگر افزایش انجام نشده باشد (چون قبلاً افزایش یافته)، باید رزرو علامت‌گذاری شود
                            reservation.personal_discount_code = pd
                            reservation.personal_discount_used = True
                            reservation.discount_processed = True
                            reservation.save(update_fields=['personal_discount_code', 'personal_discount_used', 'discount_processed'])
                            logger.info(f"کد تخفیف شخصی {discount_obj.code} برای رزرو {reservation.tracking_code} علامت‌گذاری شد. uses_count: {pd.uses_count}")
                    except Exception as e:
                        logger.error(f"خطا در مصرف کد شخصی {discount_obj.code}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        cache.delete(cache_key_discount)
                        return

        # منطق برداشت کیف پول حذف شد؛ حالا فقط در reservation/signals.py (تابع handle_reservation_payment_complete و متد کمکی _process_wallet_withdrawal) انجام می‌شود
        # جلوگیری از دو تلاش همزمان برای کسر موجودی و ساده‌سازی نقطه واحد مسئولیت.

        elif instance.capacity_status in ['confirmed', 'rejected']:
            cache.delete_many([cache_key_approval, cache_key_payment, cache_key_discount])
            logger.debug(f"تایمرها برای رزرو {instance.tracking_code} حذف شدند.")

        async_to_sync(channel_layer.group_send)(
            f"reservation_{instance.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": instance.capacity_status,
                    "timer": timer,
                },
            },
        )
        logger.debug(f"اعلان به‌روزرسانی وضعیت برای رزرو {instance.tracking_code} ارسال شد.")
    except Exception as e:
        logger.exception(f"خطا کلی در سیگنال notify_status_change_and_assign_points برای رزرو {instance.tracking_code}: {e}")
        import traceback
        logger.error(traceback.format_exc())    

# ---------------- ReservationRoom ----------------
logger = logging.getLogger(__name__)

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
        """محاسبه قیمت هر شب، قیمت نفر اضافه و مجموع قیمت اتاق."""
        if not self.room_id or not self.reservation_id:
            logger.warning(f"اتاق یا رزرو برای {self} وجود ندارد. قیمت‌ها صفر تنظیم شدند.")
            self.price_per_night = Decimal('0')
            self.extra_passenger_price = Decimal('0')
            self.fixed_discount = Decimal('0')
            self.subtotal = 0
            return

        nights = self.reservation.nights_count
        if nights <= 0:
            logger.error(f"تعداد شب‌ها برای رزرو {self.reservation.tracking_code} صفر یا منفی است.")
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
            logger.error(f"هیچ قیمت برای اتاق {self.room.title} در تاریخ {check_in_date_std} یافت نشد.")
            raise ValidationError(f"قیمت‌گذاری برای اتاق {self.room.title} در بازه زمانی مشخص‌شده یافت نشد.")

        self.price_per_night = Decimal(price_obj.price)
        self.extra_passenger_price = Decimal(price_obj.extra_passenger_price)
        if price_obj.discount_type == 'fixed' and price_obj.is_fixed_discount_one_time:
            self.fixed_discount = Decimal(price_obj.discount_value)
        else:
            self.fixed_discount = Decimal('0')

        logger.debug(
            f"محاسبه قیمت برای {self}: "
            f"price_per_night={self.price_per_night}, "
            f"extra_passenger_price={self.extra_passenger_price}, "
            f"fixed_discount={self.fixed_discount}"
        )

        room_total = self.price_per_night * self.quantity * nights
        self.subtotal = int(room_total.quantize(Decimal('1'), rounding=ROUND_UP))
        logger.debug(
            f"محاسبه مجموع قیمت برای {self}: "
            f"price_per_night={self.price_per_night}, "
            f"quantity={self.quantity}, "
            f"nights={nights}, "
            f"subtotal={self.subtotal}"
        )

    def calculate_half_day_prices(self):
        """محاسبه قیمت‌های نیم‌شارژ ورود و خروج."""
        if not self.room_id or not self.reservation_id:
            logger.warning(f"اتاق یا رزرو برای {self} وجود ندارد. نیم‌شارژ صفر تنظیم شد.")
            self.half_day_in_price = Decimal('0')
            self.half_day_out_price = Decimal('0')
            return

        hotel = self.room.hotel
        if not hotel:
            logger.error(f"هتل برای اتاق {self.room.title} یافت نشد.")
            self.half_day_in_price = Decimal('0')
            self.half_day_out_price = Decimal('0')
            return

        if self.price_per_night <= 0:
            logger.warning(f"price_per_night برای {self} صفر یا منفی است. محاسبه مجدد...")
            self.calculate_room_prices()

        half_in = Decimal('0')
        half_out = Decimal('0')

        if getattr(hotel, 'has_check_in_half_day_charge', False):
            half_in = (self.price_per_night / Decimal('2')) * self.quantity
            logger.debug(
                f"نیم‌شارژ ورود برای {self}: "
                f"price_per_night={self.price_per_night}, "
                f"quantity={self.quantity}, "
                f"half_in={half_in}"
            )
        else:
            self.half_day_in_selected = False
            logger.debug(
                f"نیم‌شارژ ورود برای {self} غیرفعال شد: "
                f"hotel_has_check_in={getattr(hotel, 'has_check_in_half_day_charge', False)}"
            )

        if getattr(hotel, 'has_check_out_half_day_charge', False):
            half_out = (self.price_per_night / Decimal('2')) * self.quantity
            logger.debug(
                f"نیم‌شارژ خروج برای {self}: "
                f"price_per_night={self.price_per_night}, "
                f"quantity={self.quantity}, "
                f"half_out={half_out}"
            )
        else:
            self.half_day_out_selected = False
            logger.debug(
                f"نیم‌شارژ خروج برای {self} غیرفعال شد: "
                f"hotel_has_check_out={getattr(hotel, 'has_check_out_half_day_charge', False)}"
            )

        self.half_day_in_price = half_in.quantize(Decimal('1'), rounding=ROUND_UP)
        self.half_day_out_price = half_out.quantize(Decimal('1'), rounding=ROUND_UP)

    def update_passenger_counts(self):
        """به‌روزرسانی تعداد مسافران اصلی و اضافه."""
        self.primary_passengers_count = self.passengers.filter(passenger_type='primary').count()
        self.extra_passengers_count = self.passengers.filter(passenger_type='extra').count()
        self.save(update_fields=['primary_passengers_count', 'extra_passengers_count'])
        logger.debug(
            f"به‌روزرسانی تعداد مسافران برای {self}: "
            f"primary={self.primary_passengers_count}, "
            f"extra={self.extra_passengers_count}"
        )

    def save(self, *args, **kwargs):
        """ذخیره مدل با محاسبه قیمت‌ها و بررسی نیم‌شارژها."""
        if not self.extra_passenger_price and self.room:
            check_in_date_std = (
                self.reservation.check_in_date.togregorian()
                if hasattr(self.reservation.check_in_date, 'togregorian')
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
                logger.debug(
                    f"قیمت نفر اضافه برای {self} از RoomDatePrice: "
                    f"{self.extra_passenger_price}"
                )

        if self.room and self.room.hotel:
            hotel = self.room.hotel
            if not getattr(hotel, 'has_check_in_half_day_charge', False):
                self.half_day_in_selected = False
                self.half_day_in_price = Decimal('0')
            if not getattr(hotel, 'has_check_out_half_day_charge', False):
                self.half_day_out_selected = False
                self.half_day_out_price = Decimal('0')
            logger.debug(
                f"تنظیمات نیم‌شارژ برای {self}: "
                f"hotel_has_check_in={getattr(hotel, 'has_check_in_half_day_charge', False)}, "
                f"hotel_has_check_out={getattr(hotel, 'has_check_out_half_day_charge', False)}"
            )

        self.calculate_room_prices()
        self.calculate_half_day_prices()
        super().save(*args, **kwargs)
        
        
        
        
# ---------------- ReservationRoomPassenger ----------------
def validate_national_code(value):
    if not value:
        raise ValidationError(_('کد شناسایی نمی‌تواند خالی باشد.'))

    # اگر کد فقط عددی با طول 10 باشد، آن را به عنوان کد ملی اعتبارسنجی کن
    if re.match(r'^\d{10}$', value):
        check_digits = int(value[9])
        total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11

        if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
            raise ValidationError(_('کد ملی معتبر نیست'))
        return value

    # در غیر این صورت، بررسی فرمت پاسپورت: طول 6 تا 9، یا تمام عدد یا حروف در ابتدا و سپس اعداد
    if 6 <= len(value) <= 9 and re.match(r'^[A-Za-z]*\d+$', value):
        return value

    raise ValidationError(_('کد شناسایی نامعتبر است. باید کد ملی ۱۰ رقمی یا شماره پاسپورت بین ۶ تا ۹ کاراکتر باشد (در صورت وجود حروف، حروف باید در ابتدای رشته قرار گیرند).'))

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
        # الزامی بودن فیلدها برای مسافر اصلی
        if self.passenger_type == 'primary':
            missing_fields = []
            for field_name in ['first_name', 'last_name', 'mobile_number', 'national_code']:
                if not getattr(self, field_name):
                    missing_fields.append(field_name)
            if missing_fields:
                raise ValidationError(f'برای مسافر اصلی، فیلدهای {missing_fields} الزامی هستند.')

        # یکتایی کد ملی در همان اتاق
        # چک یکتایی برداشته شد

    def save(self, *args, **kwargs):
        self.is_primary = self.passenger_type == 'primary'
        self.full_clean()  # اجرای تمام اعتبارسنجی‌ها قبل از ذخیره
        super().save(*args, **kwargs)
        if self.reservation_room:
            self.reservation_room.update_passenger_counts()
            if self.reservation_room.reservation:
                self.reservation_room.reservation.save()  # بازمحاسبه قیمت رزرو

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.get_passenger_type_display()})'
    
    
    
#دلایل کنسلی رزرو 
class CancellationReason(models.Model):
    title = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name="عنوان کنسلی",
        help_text="عنوانی که برای دلیل کنسلی استفاده می‌شود."
    )

    class Meta:
        verbose_name = "دلیل کنسلی"
        verbose_name_plural = "دلایل کنسلی"

    def __str__(self):
        return self.title
    
    
    
#مدل کنسلی رزرو توسط کاربر
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

    # امکان وارد کردن جریمه کنسلی به صورت درصد یا مقدار ثابت برای همین درخواست
    penalty_type = models.CharField(
        max_length=20,
        choices=PENALTY_TYPE_CHOICES,
        default='hotel_default',
        verbose_name=_('نوع جریمه'),
        help_text=_('اگر "استفاده از تنظیمات هتل" انتخاب شود، از مدل CancellationPenalty استفاده می‌شود')
    )

    penalty_value = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_('مقدار جریمه'),
        help_text=_('برای نوع "درصدی" مقدار بین 0 تا 100 وارد کنید؛ برای "مبلغ ثابت" مبلغ به تومان وارد شود.')
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
        """Validate penalty fields depending on the selected penalty_type."""
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

        # if penalty_type == 'hotel_default' then penalty_value may be None or present (ignored)

    class Meta:
        verbose_name = _('کنسل رزرو کاربر')
        verbose_name_plural = _('کنسل رزروهای کاربران')

    def process_cancellation(self):
        """
        پردازش کنسلی پس از تایید توسط ادمین:
        1. محاسبه درصد جریمه از هتل مربوطه
        2. کسر جریمه از مبلغ نهایی
        3. برگشت مبلغ باقیمانده به کیف پول کاربر
        4. ثبت مبلغ جریمه و مبلغ برگشتی در رزرو
        """
        if self.status != self.Status.APPROVED:
            raise ValidationError(_('فقط درخواست‌های تایید شده قابل پردازش هستند.'))

        reservation = self.reservation
        
        # پیدا کردن هتل مرتبط با رزرو
        hotel = reservation.get_hotel()
        if not hotel:
            raise ValidationError(_('هتل مرتبط با رزرو یافت نشد.'))

        # تعیین جریمه بر اساس نوع انتخاب‌شده در درخواست کنسلی
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

        else:
            # نوع نامشخص => بدون جریمه
            penalty_amount = Decimal('0')

        refund_amount = final_price - penalty_amount

        # اطمینان از اینکه مبلغ برگشتی منفی نشود
        if refund_amount < 0:
            refund_amount = Decimal('0')

        # برگشت وجه به کیف پول کاربر
        # به‌جای تغییر وضعیت پرداخت، از فِلاگِ thread-local برای جلوگیری از اجرای
        # سیگنالِ تخصیص امتیاز و ارسال SMS استفاده می‌کنیم تا وضعیت پرداخت دست نخورده بماند.
        with transaction.atomic():
            # اگر قبلاً امتیازها تخصیص داده شده‌اند، آن‌ها را بازگردانیم (کاهش دهیم)
            deducted_points = 0
            if getattr(reservation, 'points_assigned', False):
                total_points = 0
                for res_room in reservation.reservation_rooms.select_related('room').all():
                    room = res_room.room
                    quantity = res_room.quantity
                    points = room.customer_club_points or 0
                    total_points += points * quantity

                if total_points > 0:
                    # قفل رکورد امتیاز کاربر برای جلوگیری از race condition
                    customer_points, created = CustomerClubPoint.objects.select_for_update().get_or_create(
                        user=reservation.buyer,
                        defaults={'points': 0}
                    )
                    prev = customer_points.points
                    deducted_points = min(prev, total_points)
                    customer_points.points = prev - deducted_points
                    customer_points.save()

            # برگشت وجه به کیف پول کاربر
            wallet, created = Wallet.objects.get_or_create(user=reservation.buyer)
            wallet.balance += refund_amount
            wallet.save()

            # ثبت اطلاعات کنسلی در رزرو
            reservation.cancellation_penalty_applied = penalty_amount
            reservation.cancellation_refunded_amount = refund_amount
            reservation.cancellation_requested = True
            # وقتی کنسلی انجام می‌شود، وضعیت پرداخت رزرو نیز به 'unpaid' تغییر کند
            reservation.payment_status = 'unpaid'
            # اگر پیش از این امتیازها تخصیص داده شده بودند، آن فلگ را برداریم
            if deducted_points > 0:
                reservation.points_assigned = False

            # موقتاً سیگنال‌های ارسال امتیاز/SMS را غیرفعال می‌کنیم تا هنگام تغییر
            # وضعیت پرداخت و ذخیره‌ی رزرو، سیگنال تخصیص امتیاز اجرا نشود.
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

            # ارسال پیامک کسر امتیاز (بیرون از حالت غیرفعالِ سیگنال)
            if deducted_points > 0:
                try:
                    send_customer_club_deduct_sms(
                        reservation.buyer.phone_number,
                        reservation.buyer.first_name or reservation.buyer.phone_number,
                        deducted_points,
                        customer_points.points
                    )
                except Exception:
                    logger.exception('خطا هنگام ارسال اس‌ام‌اس کسر امتیاز')

        logger.info(
            f"کنسلی رزرو {reservation.tracking_code} پردازش شد: "
            f"جریمه {penalty_amount} تومان، برگشت {refund_amount} تومان به کیف پول"
        )

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
        help_text=_('درصد از مبلغ نهایی که به عنوان جریمه کسر می‌شود (0 تا 100)')
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
