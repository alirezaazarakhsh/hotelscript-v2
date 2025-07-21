# 📦 استاندارد کتابخانه‌های پایتون
import logging
import os
import uuid
import jdatetime
from decimal import Decimal
from datetime import timedelta
from functools import cached_property

# 🌐 Django
from django.db import models
from django.apps import apps
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

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
        verbose_name_plural = 'استان‌ها'
        
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




#مدل نوع اقامتگاه
class HotelType(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = 'نوع اقامتگاه'
        verbose_name_plural = 'نوع اقامتگاه'

    def __str__(self):
        return self.title




#مدل تگ های هتل
class HotelTag(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )

    class Meta:
        verbose_name = 'برچسب هتل'
        verbose_name_plural = 'برچسب‌ها'

    def __str__(self):
        return self.title




#مدل لمکانات رفاهی و تفریحی هتل 
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




# مدل امکانات داخلی اتاق 
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
        verbose_name=_('پرفروش ترین های صفحه اصلی '),
        default=False,
    )
    rules = models.TextField(
        verbose_name=_('قوانین و مقررات هتل '),
    )
    important_notes = models.TextField(
        verbose_name=_('نکات ضروری هتل '),
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'هتل'
        verbose_name_plural = 'هتل‌ها'

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
        verbose_name_plural = 'گالری‌های تصاویر هتل'

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
        verbose_name_plural = 'اماکن اطراف هتل'

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
    point = models.PositiveSmallIntegerField(
        verbose_name=_('امتیاز'),
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
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
        verbose_name=_('موجودی اتاق'),
        help_text=_('تعداد کل اتاق‌های قابل رزرو'),
        default=0,
        null=True,
        blank=True,
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
        if (self.count or 0) + (self.auto_approved_count or 0) > (self.inventory or 0):
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
        if self.pk:
            try:
                old_instance = Room.objects.get(pk=self.pk)
                old_inventory = old_instance.inventory or 0
                logger.debug(f"Room {self.pk}: Old inventory = {old_inventory}")
                print(f"Room {self.pk}: Old inventory = {old_inventory}")
            except Room.DoesNotExist:
                logger.error(f"Room with pk {self.pk} not found during save")
                print(f"Room with pk {self.pk} not found during save")

        super().save(*args, **kwargs)

        current_inventory = self.inventory if self.inventory is not None else 0
        logger.debug(f"Room {self.pk}: Current inventory = {current_inventory}")
        print(f"Room {self.pk}: Current inventory = {current_inventory}")

        if old_instance and old_inventory != 0 and current_inventory == 0:
            room_name = self.title or "اتاق_بانام"
            status = "اتمام_موجودی"
            hotel_name = self.hotel.name if self.hotel else None

            logger.info(f"Room {self.pk}: Inventory changed from {old_inventory} to 0 for '{room_name}', attempting to send SMS")
            print(f"Room {self.pk}: Inventory changed from {old_inventory} to 0 for '{room_name}', attempting to send SMS")

            try:
                from reservation.sms.sms import send_room_availability_sms
                success = send_room_availability_sms(room_name, status, hotel_name=hotel_name)
                if success:
                    logger.info(f"Room {self.pk}: SMS sent successfully for '{room_name}'")
                    print(f"Room {self.pk}: SMS sent successfully for '{room_name}'")
                else:
                    logger.error(f"Room {self.pk}: Failed to send SMS for '{room_name}'")
                    print(f"Room {self.pk}: Failed to send SMS for '{room_name}'")
            except Exception as e:
                logger.error(f"Room {self.pk}: Exception while sending SMS for '{room_name}': {str(e)}")
                print(f"Room {self.pk}: Exception while sending SMS for '{room_name}': {str(e)}")
    
    

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
    foreign_passenger_price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت مسافر خارجی (تومان)'),
        null=True,
        blank=True,
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
        verbose_name=_('تخفیف اولین خرید'),
        default=False,
    )

    class Meta:
        verbose_name = _('قیمت اتاق بر اساس سطح و بازه')
        verbose_name_plural = _('بازه زمانی اتاق‌ها')
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
class Passenger(models.Model):
    user = models.ForeignKey(
        BaseUser,
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
    is_foreign = models.BooleanField(
        verbose_name=_('مسافر خارجی'),
        default=False,
    )
    national_code = models.CharField(
        verbose_name=_('کد ملی'),
        max_length=10,
        validators=(
            validate_national_code,
        ),
        blank=True,
        default='',
    )
    passport_code = models.CharField(
        verbose_name=_('کد پاسپورت'),
        max_length=9,
        validators=(
            validate_passport_code,
        ),
        blank=True,
        default='',
    )
    phone_number = models.CharField(
        verbose_name=_('موبایل'),
        max_length=11,
        validators=(
            validate_phone_number,
        ),
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'مسافر'
        verbose_name_plural = 'مسافران'

    def __str__(self):
        return f'{self.user} - {self.first_name} {self.last_name}'



#مدل رزرواسیون در هتل 
class Reservation(models.Model):
    RESERVATION_STATUSES = (
        ('payment', 'در انتظار پرداخت'),
        ('pending_approve', 'در انتظار تایید ادمین'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('failed', 'ناموفق'),
        ('success', 'موفق'),
        ('expired', 'منقضی شده'),
    )

    def ten_minutes_from_now():
        return timezone.now() + timedelta(minutes=10)

    uuid = models.UUIDField(
        verbose_name=_('کد رزرو'),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        'authentication.BaseUser',
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='reservations',
    )
    room_dates = models.ManyToManyField(
        'reservation.RoomDatePrice',
        verbose_name=_('تاریخ اتاق'),
        related_name='reservations',
    )
    passengers = models.ManyToManyField(
        'reservation.Passenger',
        verbose_name=_('مسافران'),
        related_name='reservations',
    )
    extra_passengers = models.ManyToManyField(
        'reservation.Passenger',
        verbose_name=_('مسافران اضافه'),
        blank=True,
    )
    paid_price = models.PositiveBigIntegerField(
        verbose_name=_('مبلغ پرداخت شده'),
        default=0,
    )
    status = models.CharField(
        verbose_name=_('وضعیت'),
        max_length=32,
        choices=RESERVATION_STATUSES,
    )
    fail_reason = models.TextField(
        verbose_name=_('علت رد / ناموفق'),
        blank=True,
        default='',
    )
    expired_date = models.DateTimeField(
        verbose_name=_('تاریخ انقضا'),
        default=ten_minutes_from_now,
    )
    additional_details = models.TextField(
        verbose_name=_('توضیحات تکمیلی رزرواسیون'),
        blank=True,
        default='',
    )
    has_check_in_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ ورود'),
        default=False,
    )
    has_check_out_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ خروج'),
        default=False,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )
    updated = models.DateTimeField(
        verbose_name=_('تاریخ تغییر'),
        auto_now=True,
    )

    @cached_property
    def first_night_room_dates(self):
        room_dates = self.room_dates.all()
        if not room_dates:
            return []
        first_night = min(room_date.start_date for room_date in room_dates)
        return [rd for rd in room_dates if rd.start_date == first_night]

    @cached_property
    def last_night_room_dates(self):
        room_dates = self.room_dates.all()
        if not room_dates:
            return []
        last_night = max(room_date.end_date for room_date in room_dates)
        return [rd for rd in room_dates if rd.end_date == last_night]

    @cached_property
    def price(self):
        total_price = 0
        first_passenger = self.passengers.first()
        for room_date in self.room_dates.all():
            total_price += room_date.price  # توجه کن که باید در مدل RoomDatePrice فیلد price داشته باشی
            if first_passenger and first_passenger.is_foreign:
                total_price += room_date.foreign_passenger_price

        for passenger in self.extra_passengers.all():
            # توجه کن این خط ممکنه نیاز باشه فیلد extra_passenger_price از کدام room_date محاسبه شود
            # الان برای همه مسافران اضافه فقط یک room_date آخر استفاده می‌کند که شاید درست نباشد.
            # بهتر است منطق دقیقتر براساس نیاز خودت پیاده کنی
            total_price += room_date.extra_passenger_price

        if self.has_check_in_half_day_charge:
            for room_date in self.first_night_room_dates:
                total_price += room_date.price / 2

        if self.has_check_out_half_day_charge:
            for room_date in self.last_night_room_dates:
                total_price += room_date.price / 2

        return total_price
    
    def clean(self):
        passengers = list(self.passengers.all())

        if passengers:
            first_status = passengers[0].is_foreign
            if any(passenger.is_foreign != first_status for passenger in passengers):
                raise ValidationError(_('همه مسافران باید ایرانی یا همه مسافران باید خارجی باشند.'))

        for room_date in self.room_dates.all():
            room = room_date.room
            if self.passengers.count() > room.capacity:
                raise ValidationError(_(f'تعداد مسافران اصلی اتاق {room} نمی‌تواند بیشتر از {room.capacity} باشد.'))
            if self.extra_passengers.count() > room.extra_capacity:
                raise ValidationError(_(f'تعداد نفرات اضافه اتاق {room} نمی‌تواند بیشتر از {room.extra_capacity} باشد.'))

    class Meta:
        verbose_name = _('رزرواسیون')
        verbose_name_plural = _('رزرواسیون‌ها')

    def __str__(self):
        return str(self.uuid)


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