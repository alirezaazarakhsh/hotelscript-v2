from django.db import models
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.contrib.postgres.fields import ArrayField
from authentication.models import (
    BaseUser,
)
from functools import cached_property
from authentication.validators import (
    validate_phone_number,
    validate_national_code,
    validate_passport_code,
)
import uuid
from django.utils import timezone
from datetime import (
    timedelta,
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

class CommentPointItem(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    
    class Meta:
        verbose_name = 'معیار امتیازدهی'
        verbose_name_plural = 'معیارهای امتیازدهی'

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
        CommentPointItem,
        on_delete=models.CASCADE,
        verbose_name=_('معیار امتیازدهی'),
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
        return f'{self.comment} - {self.comment_point_item}'

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
    is_preferred = models.BooleanField(
        verbose_name=_('منتخب'),
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

class RoomDate(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        verbose_name=_('اتاق'),
        related_name='dates',
    )
    date = models.DateField(
        verbose_name=_('تاریخ'),
    )
    price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت (به ریال)'),
    )
    extra_passenger_price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت نفر اضافه (به ریال)'),
    )
    foreign_passenger_price = models.PositiveBigIntegerField(
        verbose_name=_('قیمت مسافر خارجی (به ریال)'),
    )
    discount = models.ForeignKey(
        RoomDateDiscount,
        on_delete=models.CASCADE,
        verbose_name=_('تخفیف'),
        related_name='room_dates',
        null=True,
    )

    @cached_property
    def final_price(self):
        if self.discount:
            if self.discount.type == 'percentage':
                discount_value = min(self.price * self.discount.value / 100, self.discount.maximum_value)
                return self.price - discount_value
            if self.discount.type == 'fixed':
                return self.price - min(self.discount.value, self.discount.maximum_value)
        return self.price

    @cached_property
    def reserved_count(self):
        # TODO
        pass

    @cached_property
    def pending_count(self):
        # TODO
        pass

    class Meta:
        verbose_name = 'تاریخ اتاق'
        verbose_name_plural = 'تاریخ‌های اتاق'
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'room',
                    'date'
                ],
                name='unique_room_date',
            )
        ]

    def __str__(self):
        return f'{self.room} - {self.date}'

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
    )
    paid_price = models.PositiveBigIntegerField(
        verbose_name=_('مبلغ پرداخت شده'),
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
        default=timezone.now() + timedelta(minutes=10)
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
