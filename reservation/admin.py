from asyncio.log import logger
from datetime import date
from decimal import Decimal
import logging
import re
import jdatetime
from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.db.models import Q
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _
from nested_admin import NestedModelAdmin, NestedTabularInline
from pydantic import ValidationError
from authentication.models import BaseUser
from reservation.forms import BestHotelsAdminForm, CityAdminForm, HotelAdminForm
from .models import (
    BestHotels,
    ClosedDate,
    HotelTagPublic,
    Province,
    City,
    HotelType,
    HotelTag,
    Facilities,
    ReservationApprovalDuration,
    Reservationhotel,
    RoomDatePrice,
    RoomFacilities,
    Hotel,
    HotelGallery,
    HotelGalleryImage,
    NearbyPlace,
    HotelFAQ,
    Comment,
    CommentPoint,
    CommentPointItem,
    RoomService,
    Room,
    Passenger,
    SEOMeta,
    SuggestedCommentItem,
    ReservationRoom,
    ReservationRoomPassenger
)



@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug',
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    form = CityAdminForm
    list_display = (
        'id',
        'name',
        'slug',
        'image',
        'province',
        'show_in_homepage',
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(HotelType)
class HotelTypeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(HotelTag)
class HotelTagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(Facilities)
class FacilitiesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'icon_preview',
    )
    search_fields = (
        'title',
        'icon__title_icon',
    )
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


@admin.register(RoomFacilities)
class RoomFacilitiesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'icon_preview',
    )
    search_fields = (
        'title',
        'icon__title_icon',
    )
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


# Inline برای SEOMeta
# فرم سفارشی برای SEOMetaInline
class SEOMetaInlineForm(forms.ModelForm):
    keywords_text = forms.CharField(
        label="کلمات کلیدی",
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        help_text="کلمات کلیدی را با کاما جدا کنید، مثل: luxury, resort, family"
    )

    class Meta:
        model = SEOMeta
        fields = ('title_tag', 'description', 'keywords_text')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.keywords:
            self.fields['keywords_text'].initial = ", ".join(self.instance.keywords)

    def save(self, commit=True):
        instance = super().save(commit=False)
        keywords_text = self.cleaned_data.get('keywords_text', '')
        instance.keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        if commit:
            instance.save()
        return instance


# Inline برای تگ عمومی
class HotelTagPublicInline(admin.TabularInline):
    model = HotelTagPublic
    extra = 3
    max_num = 3
    fields = ('title',)
    verbose_name = _('تگ عمومی ')
    verbose_name_plural = _(' تگ‌های عمومی')


# Inline برای تگ عمومی
class HotelTagPublicInline(admin.TabularInline):
    model = HotelTagPublic
    extra = 3
    max_num = 3
    fields = ('title',)
    verbose_name = _('تگ عمومی')
    verbose_name_plural = _('تگ‌های عمومی')


# Inline برای SEOMeta
class SEOMetaInline(admin.StackedInline):
    model = SEOMeta
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = 'متا سئو'
    verbose_name_plural = 'تنظیم سئوی هتل'
    fields = ('title_tag', 'keywords', 'description')
    help_texts = {
        'title_tag': 'عنوان صفحه برای سئو (حداکثر 70 کاراکتر)',
        'keywords': 'کلمات کلیدی را با "-" جدا کنید، مثل: هتل-رزرو هتل-هتل های تهران',
        'description': 'توضیحات متا برای سئو (حداکثر 160 کاراکتر)',
    }


# Admin اصلی هتل
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm

    # همه فیلدهای هتل ساده نگه داشته شده
    fields = (
        'name',
        'slug',
        'city',
        'best_logo',
        'logo_preview',
        'latitude',
        'longitude',
        'stars',
        'rating',
        'reservation_count',
        'type',
        'floors_count',
        'rooms_count',
        'check_in_time',
        'check_out_time',
        'has_check_in_half_day_charge',
        'has_check_out_half_day_charge',
        'tags',
        'facilities',
        'room_facilities',
        'is_special_offer',
        'is_flash_sale',
        'is_best_seller',
        'main_image',
        'image1',
        'image2',
        'image3',
        'image4',
        'address',
        'description',
        'further_description',
        'rules',
        'important_notes',
    )

    readonly_fields = ('logo_preview',)

    list_display = (
        'id',
        'name',
        'slug',
        'city',
        'address',
        'latitude',
        'longitude',
        'stars',
        'rating',
        'type',
        'floors_count',
        'logo_preview',
        'show_public_tags',
    )

    search_fields = ('name', 'address', 'public_tags__title')
    autocomplete_fields = ['tags', 'facilities', 'room_facilities', 'best_logo']

    # اضافه شدن inline ها
    inlines = [HotelTagPublicInline, SEOMetaInline]

    # نمایش لوگو
    def logo_preview(self, obj):
        if obj.best_logo and obj.best_logo.image_logo_hotel:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="100" height="100" style="margin-right:8px; object-fit: contain;" />'
                '</div>',
                obj.best_logo.image_logo_hotel.url
            )
        return "-"
    logo_preview.short_description = "لوگو انتخاب‌شده"

    # نمایش تگ های عمومی
    def show_public_tags(self, obj):
        qs = obj.public_tags.all()
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((tag.title,) for tag in qs)
        )
    show_public_tags.short_description = 'تگ‌های عمومی'
    

class HotelGalleryImageInline(admin.TabularInline):
    model = HotelGalleryImage
    extra = 1
    fields = ('image', 'order', 'preview',)
    readonly_fields = ('preview',)
    ordering = ('order',)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" style="object-fit: cover; border: 1px solid #ccc; border-radius: 4px;" />',
                obj.image.url
            )
        return "-"
    preview.short_description = 'پیش‌نمایش'


@admin.register(HotelGallery)
class HotelGalleryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'hotel')
    search_fields = ('title', 'hotel__name')
    autocomplete_fields = ['hotel']
    inlines = [HotelGalleryImageInline]


@admin.register(NearbyPlace)
class NearbyPlaceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'hotel',
        'distance',
        'driving_time',
        'walking_time',
        'latitude',
        'longitude',
    )
    search_fields = (
        'title',
    )


@admin.register(HotelFAQ)
class HotelFAQAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'question',
        'hotel',
        'icon_preview',
    )
    search_fields = (
        'question',
        'hotel__title',
        'icon__title_icon',
    )
    autocomplete_fields = ('hotel', 'icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'question',
                'answer',
                'hotel',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and hasattr(obj.icon, 'svg_icon') and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex; align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


class CommentPointInline(admin.TabularInline):
    model = CommentPoint
    extra = 1
    autocomplete_fields = ['comment_point_item']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'hotel',
        'text',
        'show_strengths',
        'show_weaknesses',
        'stars',
        'is_approved',
        'created_jalali',
    )
    search_fields = (
        'text',
        'strengths__title',
        'weaknesses__title',
    )
    list_filter = (
        'is_approved',
        'stars',
    )
    autocomplete_fields = ['user', 'hotel', 'suggested_items']
    exclude = ['suggested_items']
    inlines = [CommentPointInline]

    def show_strengths(self, obj):
        qs = obj.strengths.all()
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((s.title,) for s in qs)
        )
    show_strengths.short_description = 'نقاط قوت'

    def show_weaknesses(self, obj):
        qs = obj.weaknesses.all()
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((w.title,) for w in qs)
        )
    show_weaknesses.short_description = 'نقاط ضعف'

    def created_jalali(self, obj):
        if obj.created:
            return jdatetime.datetime.fromgregorian(datetime=obj.created).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    
    created_jalali.admin_order_field = 'created'
    created_jalali.short_description = 'تاریخ ایجاد (شمسی)'


@admin.register(CommentPointItem)
class CommentPointItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(SuggestedCommentItem)
class SuggestedCommentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ['title']


@admin.register(RoomService)
class RoomServiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


class RoomDateInline(admin.TabularInline):
    model = RoomDatePrice
    extra = 1
    fields = (
        'user_level',
        'start_date',
        'end_date',
        'price',
        'extra_passenger_price',
        'discount_type',
        'discount_value',
        'discount_date',
        'is_fixed_discount_one_time',
    )
    ordering = ('start_date',)


class ClosedDateInline(admin.TabularInline):
    model = ClosedDate
    extra = 1
    fields = ('date', 'user_level')
    autocomplete_fields = ('user_level',)
    ordering = ('date',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hotel',
        'title',
        'customer_club_points',
        'inventory',
        'count',
        'auto_approved_count',
        'room_capacity',
        'extra_capacity',
    )
    search_fields = ('title',)
    autocomplete_fields = ('hotel',)
    fields = (
        'hotel',
        'title',
        'description',
        'inventory',
        'count',
        'auto_approved_count',
        'customer_club_points',
        'room_capacity',
        'extra_capacity',
        'services',
    )
    inlines = [RoomDateInline]


@admin.register(RoomDatePrice)
class RoomDatePriceAdmin(admin.ModelAdmin):
    list_display = (
        'room',
        'user_level',
        'start_date',
        'end_date',
        'price',
        'discount_type',
        'discount_value',
        'discount_date',
        'is_fixed_discount_one_time',
    )
    list_filter = (
        'room',
        'user_level',
        'discount_type',
        'is_fixed_discount_one_time',
    )
    search_fields = (
        'room__title',
        'user_level__title',
    )
    autocomplete_fields = ('room', 'user_level')
    ordering = ('room', 'start_date', 'user_level')
    fieldsets = (
        (_('اطلاعات بازه و اتاق'), {
            'fields': (
                'room',
                'user_level',
                'start_date',
                'end_date',
            )
        }),
        (_('قیمت‌گذاری'), {
            'fields': (
                'price',
                'extra_passenger_price',
            )
        }),
        (_('تخفیف'), {
            'fields': (
                'discount_type',
                'discount_value',
                'discount_date',
                'is_fixed_discount_one_time',
            )
        }),
    )
    inlines = [ClosedDateInline]


# @admin.register(ClosedDate)
# class ClosedDateAdmin(admin.ModelAdmin):
#     list_display = ('room_date', 'date', 'user_level')
#     list_filter = ('room_date', 'user_level')
#     search_fields = ('room_date__room__name',)
#     autocomplete_fields = ('room_date', 'user_level')
#     ordering = ('date',)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'first_name',
        'last_name',
        'identification_code',
        'phone_number',
    )
    search_fields = (
        'first_name',
        'last_name',
        'identification_code',
        'phone_number',
    )
    
    



@admin.register(BestHotels)
class BestHotelsAdmin(admin.ModelAdmin):
    form = BestHotelsAdminForm
    list_display = (
        'order',
        'title_logo',
        'image_logo_hotel',
    )
    search_fields = (
        'title_logo',
    )
    list_filter = (
        'order',
    )


@admin.register(ReservationApprovalDuration)
class ReservationApprovalDurationAdmin(admin.ModelAdmin):
    list_display = ('duration_minutes',)
    search_fields = ('duration_minutes',)
    fields = ('duration_minutes',)
    ordering = ('duration_minutes',)

    def has_add_permission(self, request):
        count = ReservationApprovalDuration.objects.count()
        if count >= 1:
            return False
        return True
    
    
    
# Define ReservationhotelAdminForm
class ReservationhotelAdminForm(forms.ModelForm):
    class Meta:
        model = Reservationhotel
        fields = '__all__'

    def clean_check_in_date(self):
        check_in = self.cleaned_data['check_in_date']
        today_j = jdatetime.date.today()
        if check_in < today_j:
            raise ValidationError("تاریخ ورود نمی‌تواند قبل از امروز باشد.")
        return check_in

    def clean_check_out_date(self):
        check_in = self.cleaned_data.get('check_in_date')
        check_out = self.cleaned_data['check_out_date']
        if check_in and check_out <= check_in:
            raise ValidationError("تاریخ خروج باید بعد از تاریخ ورود باشد.")
        return check_out

    def clean_wallet_withdrawal_amount(self):
        amount = self.cleaned_data['wallet_withdrawal_amount']
        if amount < 0:
            raise ValidationError("مبلغ برداشت از کیف پول نمی‌تواند منفی باشد.")
        if amount > 0 and amount < 10000:
            raise ValidationError("مبلغ برداشت باید حداقل ۱۰,۰۰۰ تومان باشد.")
        return amount

class ReservationRoomPassengerInline(NestedTabularInline):
    model = ReservationRoomPassenger
    extra = 8
    max_num = 8
    fields = ('passenger_type', 'first_name', 'last_name', 'mobile_number', 'national_code')
    can_delete = True
    autocomplete_fields = ()

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and hasattr(obj, 'room') and obj.room:
            return (obj.room.room_capacity + obj.room.extra_capacity) * obj.quantity
        return self.max_num

class ReservationRoomInline(NestedTabularInline):
    model = ReservationRoom
    extra = 3
    max_num = 3
    fields = (
        'room',
        'price_per_night',
        'extra_passenger_price',
        'fixed_discount',
        'subtotal',
        'primary_passengers_count',
        'extra_passengers_count',
        'half_day_in_selected',
        'half_day_out_selected',
        'half_day_in_price',
        'half_day_out_price',
    )
    readonly_fields = (
        'primary_passengers_count',
        'extra_passengers_count',
        'half_day_in_price',
        'half_day_out_price',
    )
    show_change_link = False
    can_delete = True
    autocomplete_fields = ('room',)
    inlines = [ReservationRoomPassengerInline]

    def primary_passengers_count(self, obj):
        if obj.room:
            return obj.room.room_capacity
        return 0
    primary_passengers_count.short_description = _('تعداد نفر اصلی')

    def extra_passengers_count(self, obj):
        if obj.room:
            return obj.room.extra_capacity
        return 0
    extra_passengers_count.short_description = _('تعداد نفر اضافه')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['room'].required = False
        if 'half_day_in_selected' not in formset.form.base_fields:
            formset.form.base_fields['half_day_in_selected'] = forms.BooleanField(
                label=_('نیم‌شارژ ورود'),
                required=False,
                initial=False
            )
        if 'half_day_out_selected' not in formset.form.base_fields:
            formset.form.base_fields['half_day_out_selected'] = forms.BooleanField(
                label=_('نیم‌شارژ خروج'),
                required=False,
                initial=False
            )
        formset.form.base_fields['half_day_in_selected'].widget.attrs['class'] = 'vCheckboxField'
        formset.form.base_fields['half_day_out_selected'].widget.attrs['class'] = 'vCheckboxField'
        return formset

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj and obj.reservation_rooms.exists():
            try:
                hotel = obj.reservation_rooms.first().room.hotel
                if not getattr(hotel, 'has_check_in_half_day_charge', False):
                    if 'half_day_in_selected' in fields:
                        fields.remove('half_day_in_selected')
                if not getattr(hotel, 'has_check_out_half_day_charge', False):
                    if 'half_day_out_selected' in fields:
                        fields.remove('half_day_out_selected')
            except AttributeError:
                if 'half_day_in_selected' in fields:
                    fields.remove('half_day_in_selected')
                if 'half_day_out_selected' in fields:
                    fields.remove('half_day_out_selected')
        return fields

@admin.register(Reservationhotel)
class ReservationhotelAdmin(NestedModelAdmin):
    form = ReservationhotelAdminForm
    list_display = (
        'tracking_code', 'buyer_phone_number', 'reserver_first_name', 'reserver_last_name',
        'reserver_phone_number', 'check_in_date', 'check_out_date',
        'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'total_price_fa', 'total_extra_passenger_charge_fa', 'half_day_in_charge_fa',
        'half_day_out_charge_fa', 'total_half_day_charge_fa', 'discount_fa',
        'room_fixed_discount_fa', 'wallet_withdrawal_amount_fa', 'wallet_withdrawn_fa',
        'final_price_fa', 'capacity_status', 'payment_status',
        'points_assigned_fa', 'discount_processed_fa', 'created_jalali', 'updated_jalali'
    )
    search_fields = (
        'tracking_code', 'buyer__phone_number', 'reserver_first_name',
        'reserver_last_name', 'reserver_phone_number', 'reserver_national_code'
    )
    list_filter = ('capacity_status', 'payment_status', 'check_in_date', 'check_out_date')
    autocomplete_fields = ('buyer',)
    inlines = [ReservationRoomInline]
    readonly_fields = (
        'tracking_code', 'buyer_phone_number', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'created_jalali', 'updated_jalali', 'points_assigned_fa',
        'total_price_fa', 'total_extra_passenger_charge_fa', 'half_day_in_charge_fa',
        'half_day_out_charge_fa', 'total_half_day_charge_fa', 'discount_fa',
        'room_fixed_discount_fa', 'wallet_withdrawn_fa', 'final_price_fa',
        'discount_processed_fa','ref_id'
    )
    fieldsets = (
        (_('اطلاعات رزرو کننده'), {
            'fields': (
                'buyer', 'reserver_first_name', 'reserver_last_name',
                'reserver_phone_number', 'reserver_national_code', 'additional_notes'
            )
        }),
        (_('تاریخ رزرو'), {
            'fields': ('check_in_date', 'check_out_date')
        }),
        (_('قیمت و وضعیت'), {
            'fields': (
                'total_price_fa', 'total_extra_passenger_charge_fa', 'half_day_in_charge_fa',
                'half_day_out_charge_fa', 'total_half_day_charge_fa', 'discount_fa',
                'room_fixed_discount_fa', 'wallet_withdrawal_amount', 'wallet_withdrawn_fa',
                'final_price_fa', 'capacity_status', 'payment_status',
                'points_assigned_fa', 'discount_processed_fa','ref_id'
            )
        }),
        (_('اطلاعات سیستم'), {
            'fields': ('tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
                       'created_jalali', 'updated_jalali')
        }),
    )

    @admin.display(description=_('موبایل خریدار'))
    def buyer_phone_number(self, obj):
        if obj.buyer:
            return getattr(obj.buyer, 'phone_number', '-')
        return "-"

    @admin.display(description=_('تاریخ ایجاد (شمسی)'))
    def created_jalali(self, obj):
        if obj.created_at:
            dt = obj.created_at.togregorian() if hasattr(obj.created_at, 'togregorian') else obj.created_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'

    @admin.display(description=_('تاریخ به‌روزرسانی (شمسی)'))
    def updated_jalali(self, obj):
        if obj.updated_at:
            dt = obj.updated_at.togregorian() if hasattr(obj.updated_at, 'togregorian') else obj.updated_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'

    @admin.display(description=_('تعداد شب‌ها'))
    def nights_count_fa(self, obj):
        return obj.nights_count if obj.pk else 0

    @admin.display(description=_('کل اتاق‌ها'))
    def total_rooms_fa(self, obj):
        return obj.total_rooms if obj.pk else 0

    @admin.display(description=_('کل مهمان‌ها'))
    def total_guests_fa(self, obj):
        return obj.total_guests if obj.pk else 0

    @admin.display(description=_('مجموع قیمت'))
    def total_price_fa(self, obj):
        return "{:,}".format(obj.total_price) if obj.total_price else "-"

    @admin.display(description=_('هزینه نفر اضافه'))
    def total_extra_passenger_charge_fa(self, obj):
        return "{:,}".format(obj.total_extra_passenger_charge) if obj.total_extra_passenger_charge else "-"

    @admin.display(description=_('هزینه نیم روز ورود'))
    def half_day_in_charge_fa(self, obj):
        return "{:,}".format(obj.half_day_in_charge) if obj.half_day_in_charge else "-"

    @admin.display(description=_('هزینه نیم روز خروج'))
    def half_day_out_charge_fa(self, obj):
        return "{:,}".format(obj.half_day_out_charge) if obj.half_day_out_charge else "-"

    @admin.display(description=_('کل هزینه نیم روز'))
    def total_half_day_charge_fa(self, obj):
        return "{:,}".format(obj.total_half_day_charge) if obj.total_half_day_charge else "-"

    @admin.display(description=_('تخفیف کد'))
    def discount_fa(self, obj):
        return "{:,}".format(obj.discount) if obj.discount else "-"

    @admin.display(description=_('تخفیف ثابت اتاق'))
    def room_fixed_discount_fa(self, obj):
        return "{:,}".format(obj.room_fixed_discount) if obj.room_fixed_discount else "-"

    @admin.display(description=_('مبلغ برداشت از کیف پول'))
    def wallet_withdrawal_amount_fa(self, obj):
        return "{:,}".format(obj.wallet_withdrawal_amount) if obj.wallet_withdrawal_amount else "-"

    @admin.display(description=_('وضعیت برداشت از کیف پول'))
    def wallet_withdrawn_fa(self, obj):
        return '✓' if obj.wallet_withdrawn else '✗'
    wallet_withdrawn_fa.short_description = _('برداشت انجام شده')

    @admin.display(description=_('قیمت نهایی'))
    def final_price_fa(self, obj):
        return "{:,}".format(obj.final_price) if obj.final_price else "-"

    @admin.display(description=_('امتیازهای تخصیص داده شده'))
    def points_assigned_fa(self, obj):
        return '✓' if obj.points_assigned else '✗'
    points_assigned_fa.short_description = _('امتیازهای تخصیص داده شده')

    @admin.display(description=_('پردازش کد تخفیف انجام شده'))
    def discount_processed_fa(self, obj):
        return '✓' if obj.discount_processed else '✗'
    discount_processed_fa.short_description = _('پردازش کد تخفیف')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.reservation_rooms.exists():
            for res_room in obj.reservation_rooms.all():
                res_room.calculate_room_prices()
                res_room.calculate_half_day_prices()
                res_room.save(update_fields=[
                    'price_per_night', 'subtotal', 'fixed_discount',
                    'half_day_in_price', 'half_day_out_price',
                    'half_day_in_selected', 'half_day_out_selected'
                ])
            if not getattr(obj, '_price_calculation_done', False):
                setattr(obj, '_price_calculation_done', True)
                total_price, total_extra, discount_amount, half_day_in_charge, half_day_out_charge, total_half_day_charge, code_discount, final_price, room_fixed_discount = obj.calculate_total_price()
                obj.total_price = total_price
                obj.total_extra_passenger_charge = total_extra
                obj.discount = code_discount
                obj.room_fixed_discount = room_fixed_discount
                obj.half_day_in_charge = half_day_in_charge
                obj.half_day_out_charge = half_day_out_charge
                obj.total_half_day_charge = total_half_day_charge
                obj.final_price = final_price
                obj._skip_price_calculation = True
                obj.save(update_fields=[
                    'total_price', 'total_extra_passenger_charge', 'discount',
                    'room_fixed_discount', 'half_day_in_charge',
                    'half_day_out_charge', 'total_half_day_charge', 'final_price'
                ])

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.reservation_rooms.exists():
            for res_room in obj.reservation_rooms.all():
                if hasattr(res_room, 'calculate_half_day_prices'):
                    res_room.calculate_half_day_prices()
                    res_room.save(update_fields=['half_day_in_price', 'half_day_out_price'])
        return form