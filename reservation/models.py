# 📦 استاندارد کتابخانه‌های پایتون
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
    OuterRef, Subquery, IntegerField
)
from django.db.models.functions import Coalesce

# 🌍 Django Postgres
from django.contrib.postgres.fields import ArrayField

# 📅 Django Jalali
from django_jalali.db import models as jmodels

# 🧩 برنامه‌های داخلی پروژه
from icons.models import IconShortcut
from authentication.models import BaseUser
from authentication.validators import (
    validate_phone_number,
    validate_national_code,
    validate_passport_code
)




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
        default=1,
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
class Room(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='rooms',
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=256,
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
        blank=True,
        default='',
    )
    capacity = models.PositiveSmallIntegerField(
        verbose_name=_('ظرفیت'),
    )
    extra_capacity = models.PositiveSmallIntegerField(
        verbose_name=_('ظرفیت اضافه'),
    )
    
    customer_club_points = models.PositiveIntegerField(
        verbose_name=_('امتیاز باشگاه مشتریان'),
    )
    services = models.ManyToManyField(
        RoomService,
        verbose_name=_('خدمات'),
        related_name='rooms',
    )
    count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد'),
    )
    auto_approved_count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد بدون تایید ادمین'),
    )

    class Meta:
        verbose_name = 'اتاق'
        verbose_name_plural = 'اتاق‌ها'
        constraints = [
            models.CheckConstraint(
                check=Q(auto_approved_count__lte=F('count')),
                name='auto_approved_count_lte_count',
            )
        ]

    def __str__(self):
        return f'{self.title} - {self.hotel}'
    
    
    
    

# مدل تخفیف اتاق ها 
class RoomDateDiscount(models.Model):
    DISCOUNT_TYPES = (
        ('percentage', 'درصدی'),
        ('fixed', 'ثابت'),
    )
    type = models.CharField(
        verbose_name=_('نوع'),
        max_length=16,
        choices=DISCOUNT_TYPES,
        default='percentage',
    )
    value = models.PositiveBigIntegerField(
        verbose_name=_('مقدار تخفیف'),
    )
    maximum_value = models.PositiveBigIntegerField(
        verbose_name=_('سقف تخفیف (به ریال)'),
    )
    start_date = models.DateTimeField(
        verbose_name=_('زمان شروع تخفیف'),
    )
    end_date = models.DateTimeField(
        verbose_name=_('زمان اتمام تخفیف'),
    )
    count = models.PositiveSmallIntegerField(
        verbose_name=_('تعداد'),
    )

    class Meta:
        verbose_name = 'تخفیف اتاق'
        verbose_name_plural = 'تخفیف‌های اتاق'
        constraints = [
            models.CheckConstraint(
                check=Q(start_date__lte=F('end_date')),
                name='check_start_date_lte_end_date'
            ),
            models.CheckConstraint(
                check=Q(type='percentage', value__lte=100) | ~Q(type='percentage'),
                name='check_value_lte_100_if_percentage'
            )
        ]

    def __str__(self):
        if self.type == 'percentage':
            return f'{self.value}% - {self.start_date}'
        elif self.type == 'fixed':
            return f'{self.value} ریال - {self.start_date}'
        
        
        
    
#مدل بازه های زمانی اتاق ها
class RoomDate(models.Model):
    room = models.ForeignKey(
        'Room',
        on_delete=models.CASCADE,
        verbose_name=_('اتاق'),
        related_name='dates',
    )
    date = jmodels.jDateField(verbose_name=_('تاریخ شروع'))
    dateend = jmodels.jDateField(verbose_name=_('تاریخ پایان'))

    price = models.PositiveBigIntegerField(verbose_name=_('قیمت (تومان)'))
    extra_passenger_price = models.PositiveBigIntegerField(verbose_name=_('قیمت نفر اضافه (تومان)'))
    foreign_passenger_price = models.PositiveBigIntegerField(verbose_name=_('قیمت مسافر خارجی (تومان)'))

    discount = models.ForeignKey(
        'RoomDateDiscount',
        on_delete=models.CASCADE,
        verbose_name=_('تخفیف'),
        related_name='room_dates',
        null=True,
        blank=True,
    )

    def jalali_date(self):
        try:
            if isinstance(self.date, jdatetime.date):
                return self.date.strftime('%Y/%m/%d')
            return jdatetime.date.fromgregorian(date=self.date).strftime('%Y/%m/%d')
        except Exception:
            return 'تاریخ نامعتبر'
    jalali_date.short_description = _('تاریخ شروع شمسی')

    def jalali_dateend(self):
        try:
            if isinstance(self.dateend, jdatetime.date):
                return self.dateend.strftime('%Y/%m/%d')
            return jdatetime.date.fromgregorian(date=self.dateend).strftime('%Y/%m/%d')
        except Exception:
            return 'تاریخ نامعتبر'
    jalali_dateend.short_description = _('تاریخ پایان شمسی')

    @classmethod
    def get_occupied_statuses_count_expression(cls):
        Reservation = apps.get_model('reservation', 'Reservation')  # تغییر به Reservation
        booked_count_subquery = Reservation.objects.filter(
            room_dates=OuterRef('pk'),  # توجه: چون در مدل Reservation، فیلد room_dates است (ManyToMany)
            status='approved'  # یا هر وضعیتی که مد نظرتان است
        ).values('room_dates').annotate(
            c=Count('uuid')
        ).values('c')

        return ExpressionWrapper(
            Coalesce(Subquery(booked_count_subquery, output_field=IntegerField()), 0),
            output_field=IntegerField()
        )
        
    @classmethod
    def get_discount_count_expression(cls):
        return Coalesce(
            Case(
                When(discount__isnull=False, then=1),
                default=0,
                output_field=IntegerField(),
            ),
            0
        )

    @classmethod
    def get_discounted_price_expression(cls):
        return ExpressionWrapper(
            F('price') - (F('price') * F('discount__percent') / 100),
            output_field=PositiveBigIntegerField()
        )

    def __str__(self):
        return f'{self.room} - {self.jalali_date()}'

    class Meta:
        verbose_name = _('بازه زمانی')
        verbose_name_plural = _('بازه زمانی اتاق‌ها')
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'date'],
                name='unique_room_date',
            )
        ]
        ordering = ['room', 'date']
    

class ClosedDate(models.Model):
    room_date = models.ForeignKey(
        'RoomDate',
        on_delete=models.CASCADE,
        related_name='closed_dates',
        verbose_name=_('بازه زمانی اتاق')
    )
    date = jmodels.jDateField(verbose_name=_('تاریخ بسته شده'))  # تاریخ بسته شده به شمسی
    reason = models.CharField(max_length=255, verbose_name=_('علت بسته بودن'), blank=True, null=True)

    class Meta:
        verbose_name = _('تاریخ بسته شده')
        verbose_name_plural = _('تاریخ‌های بسته شده')
        unique_together = ('room_date', 'date')
        ordering = ['date']

    def __str__(self):
        try:
            if isinstance(self.date, jdatetime.date):
                persian_date = self.date
            else:
                persian_date = jdatetime.date.fromgregorian(date=self.date)
            return f'{self.room_date} - {persian_date.strftime("%Y/%m/%d")}'
        except Exception:
            return f'{self.room_date} - تاریخ نامعتبر'
    
    
    
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
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='reservations',
    )
    room_dates = models.ManyToManyField(
        RoomDate,
        verbose_name=_('تاریخ اتاق'),
        related_name='reservations',
    )
    passengers = models.ManyToManyField(
        Passenger,
        verbose_name=_('مسافران'),
        related_name='reservations',
    )
    extra_passengers = models.ManyToManyField(
        Passenger,
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
        # TODO: read from approve time config
        default=ten_minutes_from_now,
    )
    additional_details = models.TextField(
        verbose_name=_('توضیحات تکمیلی رزرواسیون'),
        blank=True,
        default='',
    )
    has_check_in_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ ورود'),
    )
    has_check_out_half_day_charge = models.BooleanField(
        verbose_name=_('نیم شارژ خروج'),
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
        first_night = min(map(lambda room_date: room_date.date, room_dates))
        return filter(lambda room_date: room_date.date == first_night, room_dates)

    @cached_property
    def last_night_room_dates(self):
        room_dates = self.room_dates.all()
        last_night = max(map(lambda room_date: room_date.date, room_dates))
        return filter(lambda room_date: room_date.date == last_night, room_dates)

    @cached_property
    def price(self):
        total_price = 0

        for room_date in self.room_dates.all():
            total_price += room_date.final_price
            if self.passengers.first().is_foreign:
                total_price += room_date.foreign_passenger_price

        for passenger in self.extra_passengers.all():
            total_price += room_date.extra_passenger_price
        
        if self.has_check_in_half_day_charge:
            for room_date in self.first_night_room_dates:
                total_price += room_date.final_price / 2
        
        if self.has_check_out_half_day_charge:
            for room_date in self.last_night_room_dates:
                total_price += room_date.final_price / 2
        
        return total_price
    
    def clean(self):
        passengers = self.passengers.all()
        
        if passengers:
            first_status = passengers[0].is_foreign
            if any(passenger.is_foreign != first_status for passenger in passengers):
                raise ValidationError('همه مسافران باید ایرانی یا همه مسافران باید خارجی باشند.')

        for room_date in self.room_dates.all():
            room = room_date.room
            if self.passengers.count() > room.capacity:
                raise ValidationError(f'تعداد مسافران اصلی اتاق {room} نمی‌تواند بیشتر از {room.capacity} باشد.')
            if self.extra_passengers.count() > room.extra_capacity:
                raise ValidationError(f'تعداد نفرات اضافه اتاق {room} نمی‌تواند بیشتر از {room.extra_capacity} باشد.')

    class Meta:
        verbose_name = 'رزرواسیون'
        verbose_name_plural = 'رزرواسیون‌ها'

    def __str__(self):
        return f'{self.uuid}'



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