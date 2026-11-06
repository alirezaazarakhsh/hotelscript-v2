import logging
import re
from datetime import date
from decimal import Decimal
import jdatetime

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _
from nested_admin import NestedModelAdmin, NestedTabularInline

from authentication.models import BaseUser
from reservation.forms import (
    BestHotelsAdminForm, 
    CityAdminForm, 
    HotelAdminForm, 
    ReservationInvoiceSettingsAdminForm
)
from .models import (
    Country,
    Province,
    City,
    HotelType,
    HotelTag,
    HotelTagPublic,
    Facilities,
    RoomFacilities,
    BestHotels,
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
    RoomDatePrice,
    ClosedDate,
    ReservationApprovalDuration,
    Passenger,
    SEOMeta,
    Reservationhotel,
    ReservationRoom,
    ReservationRoomPassenger,
    CancellationReason,
    UserCancellation,
    CancellationPenalty,
    ReservationInvoiceSettings,
    SnappTripSetting,
    SnappHotelDirectory,
    SuggestedCommentItem
)
from .snapptrip_service import (
    sync_all_snapptrip_hotels_directory, 
    sync_hotel_and_rooms_from_snapp,
    get_snapptrip_booking_status,
    get_snapptrip_wallet_balance,
    confirm_snapptrip_booking
)

logger = logging.getLogger(__name__)


# ==============================================================================
# بخش ۱: کشور، استان، شهر و تعاریف پایه
# ==============================================================================

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'flag_preview', 'name', 'code', 'slug')
    search_fields = ('name', 'code', 'slug')
    readonly_fields = ('flag_preview_large',)
    fields = ('name', 'slug', 'code', 'flag_preview_large')

    def flag_preview(self, obj):
        if obj.flag_url:
            return format_html(
                '<img src="{}" width="30" height="20" style="object-fit:cover; border:1px solid #ddd; border-radius:3px; vertical-align:middle;" />',
                obj.flag_url
            )
        return "-"
    flag_preview.short_description = "پرچم"

    def flag_preview_large(self, obj):
        if obj.flag_url:
            return format_html(
                '<div>'
                '<img src="{}" width="90" height="60" style="object-fit:cover; border:1px solid #ccc; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.15);" />'
                '<p style="margin-top:6px; color:#555; font-size:12px;">کد پرچم: {} | <a href="{}" target="_blank">مشاهده SVG مستقیم</a></p>'
                '</div>',
                obj.flag_url, obj.code, obj.flag_url
            )
        return "کد ۲ حرفی کشور را ذخیره کنید تا پرچم به صورت آنلاین نمایش داده شود."
    flag_preview_large.short_description = "پیش‌نمایش پرچم"


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'country_flag', 'country', 'slug')
    search_fields = ('name', 'slug', 'country__name')
    list_filter = ('country',)
    autocomplete_fields = ('country',)

    def country_flag(self, obj):
        if obj.country and obj.country.flag_url:
            return format_html(
                '<img src="{}" width="24" height="16" style="object-fit:cover; border:1px solid #ddd; border-radius:2px; vertical-align:middle;" />',
                obj.country.flag_url
            )
        return "-"
    country_flag.short_description = "پرچم کشور"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    form = CityAdminForm
    list_display = ('id', 'name', 'slug', 'image', 'province', 'show_in_homepage')
    search_fields = ('name', 'slug', 'province__name')
    list_filter = ('province', 'show_in_homepage')
    autocomplete_fields = ('province',)


@admin.register(HotelType)
class HotelTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)


@admin.register(HotelTag)
class HotelTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)


@admin.register(Facilities)
class FacilitiesAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'icon_preview')
    search_fields = ('title', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'icon', 'icon_preview')}),
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
    list_display = ('id', 'title', 'icon_preview')
    search_fields = ('title', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'icon', 'icon_preview')}),
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


# مدل‌های کمکی که از منوی سایدبار مخفی هستند
@admin.register(RoomService)
class RoomServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)

    def has_module_permission(self, request):
        return False


@admin.register(SuggestedCommentItem)
class SuggestedCommentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)

    def has_module_permission(self, request):
        return False


@admin.register(CommentPointItem)
class CommentPointItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_positive', 'is_negative')
    search_fields = ('title',)

    def has_module_permission(self, request):
        return False


# ==============================================================================
# بخش ۲: اینلاین کامل اتاق درون هتل (شامل تمام فیلدها + دکمه تقویم و نرخ)
# ==============================================================================

class RoomInline(admin.StackedInline):
    """
    اینلاین جامع اتاق‌ها درون صفحه هتل:
    شامل تمام مشخصات اتاق + دکمه باز کردن اختصاصی تقویم و قیمت‌ها
    """
    model = Room
    extra = 0
    filter_horizontal = ('services',)
    verbose_name = 'اتاق'
    verbose_name_plural = 'اتاق‌های این هتل'

    fieldsets = (
        ('مشخصات اصلی و ظرفیت اتاق', {
            'fields': (
                ('title', 'board_type'),
                ('room_capacity', 'extra_capacity'),
                ('inventory', 'count', 'auto_approved_count'),
                'customer_club_points',
                'services',
                'description',
                'rules',
                ('snapptrip_room_id', 'is_snapptrip'),
                'price_calendar_button',
            )
        }),
    )
    readonly_fields = ('price_calendar_button',)

    def price_calendar_button(self, obj):
        if obj and obj.pk:
            url = reverse('admin:reservation_room_change', args=[obj.pk]) + '?_popup=1&prices_only=1'
            return format_html(
                '<div style="margin: 10px 0; padding: 10px; background: #f8fafc; border: 1px dashed #0284c7; border-radius: 6px;">'
                '<a class="button" style="background:#0284c7; color:white; padding:8px 16px; border-radius:4px; font-size:13px; font-weight:bold; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 4px rgba(2,132,199,0.25);" '
                'onclick="window.open(\'{url}\', \'prices_{id}\', \'width=1150,height=750,top=100,left=150,resizable=yes,scrollbars=yes\'); return false;" href="{url}">'
                '📅 باز کردن تقویم و قیمت‌های این اتاق (کلیک کنید)'
                '</a>'
                '<span style="margin-right:12px; font-size:12px; color:#475569;">(با کلیک روی این دکمه فقط جدول بازه‌های زمانی و قیمت‌های این اتاق برای ویرایش باز می‌شود)</span>'
                '</div>',
                url=url, id=obj.pk
            )
        return format_html('<span style="color:#64748b; font-size:12px;">(پس از ذخیره هتل، دکمه تنظیم تقویم و قیمت برای این اتاق جدید فعال خواهد شد)</span>')
    price_calendar_button.short_description = "تقویم و نرخ‌گذاری"


class SEOMetaInlineForm(forms.ModelForm):
    keywords_text = forms.CharField(
        label="کلمات کلیدی",
        required=False,
        widget=forms.TextInput(attrs={'style': 'width: 100%;'}),
        help_text="کلمات کلیدی را با کاما جدا کنید، مثل: هتل، رزرو هتل، هتل های مشهد"
    )

    class Meta:
        model = SEOMeta
        fields = ('title_tag', 'description', 'keywords_text')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.keywords:
            if isinstance(self.instance.keywords, list):
                self.fields['keywords_text'].initial = ", ".join(self.instance.keywords)
            elif isinstance(self.instance.keywords, str):
                cleaned = self.instance.keywords.replace('-', ', ')
                self.fields['keywords_text'].initial = cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        keywords_text = self.cleaned_data.get('keywords_text', '')
        keywords_list = [k.strip() for k in keywords_text.split(',') if k.strip()]
        instance.keywords = ", ".join(keywords_list)
        if commit:
            instance.save()
        return instance


class SEOMetaInline(admin.StackedInline):
    model = SEOMeta
    form = SEOMetaInlineForm
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = 'سئو و متاتگ‌ها'
    verbose_name_plural = 'تنظیمات سئوی هتل'
    fields = ('title_tag', 'keywords_text', 'description', 'canonical_url', 'og_title', 'og_description', 'og_image', 'no_index')


class HotelTagPublicInline(admin.TabularInline):
    model = HotelTagPublic
    extra = 2
    max_num = 3
    fields = ('title',)
    verbose_name = _('تگ عمومی')
    verbose_name_plural = _('تگ‌های عمومی هتل')


class HotelFAQInline(admin.StackedInline):
    model = HotelFAQ
    extra = 1
    verbose_name = 'سوال متداول'
    verbose_name_plural = 'سوالات متداول هتل'
    fields = ('question', 'answer')


class NearbyPlaceInline(admin.TabularInline):
    model = NearbyPlace
    extra = 0
    verbose_name = 'مکان نزدیک'
    verbose_name_plural = 'اماکن مهم و دیدنی اطراف هتل'
    fields = ('title', 'distance', 'driving_time', 'walking_time', 'latitude', 'longitude', 'image')


class CancellationPenaltyInline(admin.StackedInline):
    model = CancellationPenalty
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = 'درصد جریمه کنسلی'
    verbose_name_plural = 'قوانین جریمه کنسلی هتل'
    fields = ('penalty_percentage',)


# ==============================================================================
# بخش ۳: مدیریت هتل‌ها
# ==============================================================================

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm

    fieldsets = (
        ('وضعیت انتشار هتل', {
            'fields': ('status',),
            'description': 'اگر هنوز تمام اطلاعات و عکس‌های هتل آماده نیست، وضعیت را روی «پیش‌نویس» بگذارید.'
        }),
        ('اطلاعات پایه هتل', {
            'fields': (
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
        }),
        ('اتصال به اسنپ‌تریپ (B2B SnappTrip)', {
            'fields': (
                'snapptrip_hotel_id',
                'sync_from_snapptrip',
                'is_snapptrip',
            ),
            'description': 'شناسه هتل در اسنپ را وارد کرده و تیک همگام‌سازی را فعال کنید.'
        }),
    )

    readonly_fields = ('logo_preview',)

    list_display = (
        'id',
        'name',
        'city',
        'status_colored',
        'snapptrip_hotel_id',
        'is_snapptrip',
        'sync_button_display',
        'stars',
        'rating',
        'type',
        'logo_preview',
        'show_public_tags',
    )

    search_fields = ('name', 'address', 'public_tags__title', 'snapptrip_hotel_id')
    autocomplete_fields = ['tags', 'facilities', 'room_facilities', 'best_logo', 'city']
    list_filter = ('status', 'is_snapptrip', 'city', 'type', 'stars')

    # اینلاین اتاق‌ها دقیقاً زیر جریمه کنسلی قرار دارند
    inlines = [
        HotelTagPublicInline, 
        SEOMetaInline, 
        HotelFAQInline, 
        NearbyPlaceInline, 
        CancellationPenaltyInline,  # جریمه کنسلی
        RoomInline                  # اتاق‌های هتل
    ]

    @admin.display(description="وضعیت انتشار", ordering="status")
    def status_colored(self, obj):
        if obj.status == 'published':
            return format_html('<span style="color:white; background:#28a745; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">منتشر شده</span>')
        return format_html('<span style="color:#333; background:#ffc107; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">پیش‌نویس</span>')

    def sync_button_display(self, obj):
        if obj.snapptrip_hotel_id:
            url = reverse('admin:hotel-sync-snapp', args=[obj.pk])
            return format_html(
                '<a class="button" style="background:#28a745; color:white; padding:4px 10px; border-radius:4px; text-decoration:none;" href="{}">دریافت اتاق‌ها از اسنپ</a>',
                url
            )
        return "-"
    sync_button_display.short_description = "عملیات اسنپ"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:hotel_id>/sync-snapp/',
                self.admin_site.admin_view(self.sync_snapp_action),
                name='hotel-sync-snapp',
            ),
        ]
        return custom_urls + urls

    def sync_snapp_action(self, request, hotel_id):
        success, msg = sync_hotel_and_rooms_from_snapp(hotel_id)
        if success:
            self.message_user(request, msg, messages.SUCCESS)
        else:
            self.message_user(request, msg, messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '/admin/reservation/hotel/'))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.sync_from_snapptrip and obj.snapptrip_hotel_id:
            success, msg = sync_hotel_and_rooms_from_snapp(obj.id)
            if success:
                self.message_user(request, msg, messages.SUCCESS)
            else:
                self.message_user(request, msg, messages.ERROR)

    def logo_preview(self, obj):
        if obj.best_logo and obj.best_logo.image_logo_hotel:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="80" height="80" style="object-fit: contain;" />'
                '</div>',
                obj.best_logo.image_logo_hotel.url
            )
        return "-"
    logo_preview.short_description = "لوگو انتخاب‌شده"

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


# ==============================================================================
# بخش ۴: گالری عکس‌های هتل
# ==============================================================================

class HotelGalleryImageInline(admin.TabularInline):
    model = HotelGalleryImage
    extra = 1
    fields = ('image', 'preview',)
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border: 1px solid #ccc; border-radius: 4px;" />',
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


# ==============================================================================
# بخش ۵: نظرات هتل‌ها
# ==============================================================================

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
    search_fields = ('text', 'strengths__title', 'weaknesses__title')
    list_filter = ('is_approved', 'stars')
    autocomplete_fields = ['user', 'hotel']
    exclude = ['suggested_items']
    inlines = [CommentPointInline]

    def show_strengths(self, obj):
        qs = obj.strengths.all()
        if not qs.exists():
            return "-"
        return format_html_join(mark_safe('<br>'), '{}', ((s.title,) for s in qs))
    show_strengths.short_description = 'نقاط قوت'

    def show_weaknesses(self, obj):
        qs = obj.weaknesses.all()
        if not qs.exists():
            return "-"
        return format_html_join(mark_safe('<br>'), '{}', ((w.title,) for w in qs))
    show_weaknesses.short_description = 'نقاط ضعف'

    def created_jalali(self, obj):
        if obj.created:
            return jdatetime.datetime.fromgregorian(datetime=obj.created).strftime('%Y/%m/%d %H:%M')
        return '-'
    created_jalali.admin_order_field = 'created'
    created_jalali.short_description = 'تاریخ ایجاد (شمسی)'


# ==============================================================================
# بخش ۶: مدیریت مستقل اتاق‌ها (نمایش اختصاصی تقویم و قیمت در حالت پاپ‌آپ)
# ==============================================================================

class RoomDateInline(admin.TabularInline):
    model = RoomDatePrice
    extra = 1
    fields = (
        'user_level',
        'start_date',
        'end_date',
        'purchase_price',
        'price',
        'extra_passenger_price',
        'discount_type',
        'discount_value',
        'discount_date',
        'is_fixed_discount_one_time',
    )
    ordering = ('start_date',)
    verbose_name = 'بازه زمانی و قیمت اتاق'
    verbose_name_plural = 'بازه‌های زمانی و قیمت‌های این اتاق'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        try:
            formset.form.base_fields['purchase_price'].required = False
        except Exception:
            pass
        return formset


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hotel',
        'title',
        'snapptrip_room_id',
        'board_type',
        'is_snapptrip',
        'inventory',
        'count',
        'auto_approved_count',
        'room_capacity',
        'extra_capacity',
    )
    search_fields = ('title', 'hotel__name', 'snapptrip_room_id')
    list_filter = ('is_snapptrip', 'board_type', 'hotel')
    autocomplete_fields = ('hotel',)
    filter_horizontal = ('services',)

    fields = (
        'hotel',
        'title',
        'description',
        'rules',
        'snapptrip_room_id',
        'board_type',
        'is_snapptrip',
        'inventory',
        'count',
        'auto_approved_count',
        'customer_club_points',
        'room_capacity',
        'extra_capacity',
        'services',
    )

    inlines = [RoomDateInline]

    def room_info_display(self, obj):
        if not obj:
            return "-"
        hotel_name = obj.hotel.name if obj.hotel else "نامشخص"
        return format_html(
            '<div style="background:#f0fdf4; border:1px solid #86efac; padding:12px 18px; border-radius:8px; margin-bottom:12px;">'
            '<h3 style="margin:0 0 6px 0; color:#166534; font-size:15px; font-weight:bold;">🏨 هتل: {} &nbsp;|&nbsp; 🛏️ اتاق: {}</h3>'
            '<p style="margin:0; color:#15803d; font-size:12px;">مشخصات کلی اتاق در صفحه هتل ذخیره می‌شود. در جدول زیر فقط بازه‌های زمانی و قیمت‌های این اتاق را تعریف یا ویرایش کرده و دکمه <b>ذخیره</b> در پایین را بزنید.</p>'
            '</div>',
            hotel_name, obj.title or f"اتاق {obj.pk}"
        )
    room_info_display.short_description = "مشخصات اتاق"

    def get_fieldsets(self, request, obj=None):
        # اگر دکمه از داخل هتل کلیک شده باشد، فقط جدول بازه‌های زمانی نمایش داده می‌شود
        if request.GET.get('prices_only'):
            return (
                (None, {
                    'fields': ('room_info_display',)
                }),
            )
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if request.GET.get('prices_only'):
            readonly.append('room_info_display')
        return readonly


# ==============================================================================
# بخش ۷: مسافران و برندها (با پیش‌نمایش لوگو)
# ==============================================================================

@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'identification_code', 'phone_number')
    search_fields = ('first_name', 'last_name', 'identification_code', 'phone_number')


@admin.register(BestHotels)
class BestHotelsAdmin(admin.ModelAdmin):
    form = BestHotelsAdminForm
    list_display = ('order', 'logo_preview', 'title_logo')
    search_fields = ('title_logo',)
    list_filter = ('order',)
    readonly_fields = ('logo_preview_large',)
    fields = ('order', 'title_logo', 'image_logo_hotel', 'logo_preview_large')

    def logo_preview(self, obj):
        if obj.image_logo_hotel:
            return format_html(
                '<img src="{}" style="height: 38px; width: 75px; object-fit: contain; border-radius: 4px; border: 1px solid #ddd; background: #fafafa; padding: 2px;" />',
                obj.image_logo_hotel.url
            )
        return "-"
    logo_preview.short_description = "پیش‌نمایش لوگو"

    def logo_preview_large(self, obj):
        if obj.image_logo_hotel:
            return format_html(
                '<img src="{}" style="max-height: 120px; max-width: 250px; object-fit: contain; border-radius: 6px; border: 1px solid #ccc; padding: 4px;" />',
                obj.image_logo_hotel.url
            )
        return "هنوز تصویری انتخاب نشده است."
    logo_preview_large.short_description = "پیش‌نمایش تصویر انتخاب‌شده"


# ==============================================================================
# بخش ۸: مدیریت رزروها (بدون هیچ فیلتر)
# ==============================================================================

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
    extra = 0
    max_num = 10
    fields = ('passenger_type', 'first_name', 'last_name', 'mobile_number', 'national_code')
    can_delete = True


class ReservationRoomInline(NestedTabularInline):
    model = ReservationRoom
    extra = 1
    max_num = 10
    fields = (
        'room', 'price_per_night', 'extra_passenger_price', 'fixed_discount', 'subtotal',
        'primary_passengers_count', 'extra_passengers_count',
        'half_day_in_selected', 'half_day_out_selected', 'half_day_in_price', 'half_day_out_price',
    )
    readonly_fields = (
        'primary_passengers_count', 'extra_passengers_count',
        'half_day_in_price', 'half_day_out_price',
    )
    show_change_link = False
    can_delete = True
    autocomplete_fields = ('room',)
    inlines = [ReservationRoomPassengerInline]

    def primary_passengers_count(self, obj):
        return obj.room.room_capacity if obj.room else 0
    primary_passengers_count.short_description = _('تعداد نفر اصلی')

    def extra_passengers_count(self, obj):
        return obj.room.extra_capacity if obj.room else 0
    extra_passengers_count.short_description = _('تعداد نفر اضافه')


@admin.register(Reservationhotel)
class ReservationhotelAdmin(NestedModelAdmin):
    form = ReservationhotelAdminForm
    list_display = (
        'tracking_code', 'buyer_phone_number', 'reserver_first_name', 'reserver_last_name',
        'check_in_date', 'check_out_date', 'nights_count_fa',
        'total_price_fa', 'final_price_fa',
        'capacity_status_colored', 'payment_status_colored',
        'snapp_code_fa',
        'snapp_status_colored',
        'cancellation_requested_fa',
        'created_jalali'
    )
    search_fields = (
        'tracking_code', 'buyer__phone_number', 'reserver_first_name',
        'reserver_last_name', 'reserver_phone_number', 'reserver_national_code',
        'snapp_reservation_code',
    )
    list_filter = ()

    autocomplete_fields = ('buyer',)
    inlines = [ReservationRoomInline]
    actions = ['confirm_snapp_action_bulk']
    readonly_fields = (
        'tracking_code', 'buyer_phone_number', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'created_jalali', 'updated_jalali', 'points_assigned_fa',
        'total_price_fa', 'total_extra_passenger_charge_fa', 'half_day_in_charge_fa',
        'half_day_out_charge_fa', 'total_half_day_charge_fa', 'discount_fa',
        'room_fixed_discount_fa', 'wallet_withdrawn_fa', 'final_price_fa',
        'discount_processed_fa', 'ref_id',
        'personal_discount_code', 'personal_discount_used',
        'cancellation_penalty_fa', 'cancellation_refunded_fa', 'cancellation_requested_fa',
        'is_snapptrip_reservation', 'snapp_reservation_code', 'snapp_status',
    )

    fieldsets = (
        (_('اطلاعات رزرو کننده'), {
            'fields': (
                'buyer', 'reserver_first_name', 'reserver_last_name',
                'reserver_phone_number', 'reserver_national_code', 'additional_notes'
            )
        }),
        (_('تاریخ اقامت'), {
            'fields': ('check_in_date', 'check_out_date')
        }),
        (_('قیمت و وضعیت مالی'), {
            'fields': (
                'total_price_fa', 'total_extra_passenger_charge_fa', 'half_day_in_charge_fa',
                'half_day_out_charge_fa', 'total_half_day_charge_fa', 'discount_fa',
                'room_fixed_discount_fa', 'wallet_withdrawal_amount', 'wallet_withdrawn_fa',
                'final_price_fa', 'capacity_status', 'payment_status',
                'points_assigned_fa', 'discount_processed_fa', 'ref_id'
            )
        }),
        (_('وضعیت وب‌سرویس اسنپ‌تریپ'), {
            'fields': (
                'is_snapptrip_reservation',
                'snapp_reservation_code',
                'snapp_status',
            ),
        }),
        (_('کنسلی'), {
            'fields': (
                'cancellation_penalty_fa',
                'cancellation_refunded_fa',
                'cancellation_requested_fa',
            ),
        }),
        (_('اطلاعات سیستم'), {
            'fields': ('tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
                       'created_jalali', 'updated_jalali')
        }),
    )

    @admin.display(description='کد رزرو اسنپ')
    def snapp_code_fa(self, obj):
        if obj.snapp_reservation_code:
            url = reverse('admin:reservation-check-snapp-status', args=[obj.pk])
            return format_html(
                '<a href="{}" title="کلیک برای استعلام آنلاین وضعیت" style="font-family: monospace; font-weight: bold; color: #007bff; background: #e7f1ff; padding: 2px 6px; border-radius: 4px; text-decoration: none;">🔍 {}</a>',
                url, obj.snapp_reservation_code
            )
        return "-"

    @admin.display(description='وضعیت در اسنپ')
    def snapp_status_colored(self, obj):
        if not obj.is_snapptrip_reservation:
            return format_html('<span style="color:#aaa;">رزرو مستقیم</span>')

        status_colors = {
            'confirmed': ('#28a745', 'تأیید نهایی'),
            'availability_confirmed': ('#28a745', 'تأیید ظرفیت هتل'),
            'availability_checking': ('#e0a800', 'در حال استعلام'),
            'payment_on': ('#17a2b8', 'قفل موقت ۱۵ دقیقه'),
            'draft': ('#6c757d', 'پیش‌نویس'),
            'insufficient_credit': ('#fd7e14', 'کسری کیف‌پول اسنپ ⚠️'),
            'failed': ('#dc3545', 'ناموفق'),
        }
        color, label = status_colors.get(obj.snapp_status, ('#6c757d', obj.snapp_status or 'نامشخص'))
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, label
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:reservation_id>/check-snapp-status/', self.admin_site.admin_view(self.check_snapp_status_action), name='reservation-check-snapp-status'),
            path('<int:reservation_id>/confirm-snapp/', self.admin_site.admin_view(self.confirm_snapp_action), name='reservation-confirm-snapp'),
        ]
        return custom_urls + urls

    def check_snapp_status_action(self, request, reservation_id):
        obj = self.get_object(request, reservation_id)
        if not obj or not obj.snapp_reservation_code:
            self.message_user(request, "این رزرو کد اسنپ ندارد.", messages.WARNING)
            return redirect(reverse('admin:reservation_reservationhotel_change', args=[reservation_id]))

        try:
            status_name, raw_res = get_snapptrip_booking_status(obj.snapp_reservation_code)
            obj.snapp_status = str(status_name)[:30]
            obj.save(update_fields=['snapp_status'])
            balance, _ = get_snapptrip_wallet_balance()
            msg = f"🔍 وضعیت در اسنپ: {status_name} | موجودی کیف‌پول اسنپ: {int(balance):,} تومان"
            self.message_user(request, msg, messages.INFO)
        except Exception as e:
            self.message_user(request, f"خطا در استعلام اسنپ: {e}", messages.ERROR)
        return redirect(reverse('admin:reservation_reservationhotel_change', args=[reservation_id]))

    def confirm_snapp_action(self, request, reservation_id):
        obj = self.get_object(request, reservation_id)
        if not obj or not obj.snapp_reservation_code:
            self.message_user(request, "این رزرو کد اسنپ ندارد.", messages.WARNING)
            return redirect(reverse('admin:reservation_reservationhotel_change', args=[reservation_id]))

        try:
            from .snapptrip_service import auto_confirm_snapp_reservation_if_charged
            success, msg = auto_confirm_snapp_reservation_if_charged(obj)
            if success:
                self.message_user(request, f"✅ {msg}", messages.SUCCESS)
            else:
                self.message_user(request, f"⚠️ {msg}", messages.WARNING)
        except Exception as e:
            self.message_user(request, f"خطای ارتباط با اسنپ: {e}", messages.ERROR)
        return redirect(reverse('admin:reservation_reservationhotel_change', args=[reservation_id]))

    @admin.action(description="✅ تایید قطعی رزروهای انتخاب‌شده در اسنپ")
    def confirm_snapp_action_bulk(self, request, queryset):
        from .snapptrip_service import auto_confirm_snapp_reservation_if_charged
        success_count = 0
        for obj in queryset.filter(is_snapptrip_reservation=True, snapp_reservation_code__isnull=False):
            try:
                ok, _ = auto_confirm_snapp_reservation_if_charged(obj)
                if ok:
                    success_count += 1
            except Exception:
                pass
        self.message_user(request, f"تعداد {success_count} رزرو با موفقیت در اسنپ قطعی شدند.", messages.SUCCESS)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj and obj.snapp_reservation_code:
            check_url = reverse('admin:reservation-check-snapp-status', args=[obj.pk])
            confirm_url = reverse('admin:reservation-confirm-snapp', args=[obj.pk])
            extra_context['title'] = format_html(
                '{} &nbsp;&nbsp; '
                '<a class="button" style="background:#17a2b8; color:white; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:12px;" href="{}">🔍 استعلام اسنپ</a> &nbsp;'
                '<a class="button" style="background:#28a745; color:white; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:12px;" onclick="return confirm(\'آیا از تایید نهایی در اسنپ مطمئن هستید؟\');" href="{}">✅ تایید نهایی در اسنپ</a>',
                f"ویرایش رزرو {obj.tracking_code}",
                check_url,
                confirm_url
            )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    @admin.display(description=_('موبایل خریدار'))
    def buyer_phone_number(self, obj):
        return getattr(obj.buyer, 'phone_number', '-') if obj.buyer else "-"

    @admin.display(description=_('تاریخ ثبت'))
    def created_jalali(self, obj):
        if obj.created_at:
            dt = obj.created_at.togregorian() if hasattr(obj.created_at, 'togregorian') else obj.created_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M')
        return '-'

    @admin.display(description=_('تاریخ به‌روزرسانی'))
    def updated_jalali(self, obj):
        if obj.updated_at:
            dt = obj.updated_at.togregorian() if hasattr(obj.updated_at, 'togregorian') else obj.updated_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M')
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

    @admin.display(description=_('هزینه نیم‌روز ورود'))
    def half_day_in_charge_fa(self, obj):
        return "{:,}".format(obj.half_day_in_charge) if obj.half_day_in_charge else "-"

    @admin.display(description=_('هزینه نیم‌روز خروج'))
    def half_day_out_charge_fa(self, obj):
        return "{:,}".format(obj.half_day_out_charge) if obj.half_day_out_charge else "-"

    @admin.display(description=_('کل هزینه نیم‌روز'))
    def total_half_day_charge_fa(self, obj):
        return "{:,}".format(obj.total_half_day_charge) if obj.total_half_day_charge else "-"

    @admin.display(description=_('تخفیف'))
    def discount_fa(self, obj):
        return "{:,}".format(obj.discount) if obj.discount else "-"

    @admin.display(description=_('تخفیف اتاق'))
    def room_fixed_discount_fa(self, obj):
        return "{:,}".format(obj.room_fixed_discount) if obj.room_fixed_discount else "-"

    @admin.display(description=_('برداشت از کیف پول'))
    def wallet_withdrawal_amount_fa(self, obj):
        return "{:,}".format(obj.wallet_withdrawal_amount) if obj.wallet_withdrawal_amount else "-"

    @admin.display(description=_('برداشت انجام شده'), boolean=True)
    def wallet_withdrawn_fa(self, obj):
        return obj.wallet_withdrawn

    @admin.display(description=_('قیمت نهایی'))
    def final_price_fa(self, obj):
        return "{:,}".format(obj.final_price) if obj.final_price else "-"

    @admin.display(description=_('امتیاز باشگاه'), boolean=True)
    def points_assigned_fa(self, obj):
        return obj.points_assigned

    @admin.display(description=_('پردازش تخفیف'), boolean=True)
    def discount_processed_fa(self, obj):
        return obj.discount_processed

    @admin.display(description='جریمه کنسلی')
    def cancellation_penalty_fa(self, obj):
        if obj.cancellation_penalty_applied > 0:
            formatted_value = "{:,}".format(int(obj.cancellation_penalty_applied))
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', formatted_value)
        return "-"

    @admin.display(description='مبلغ برگشتی')
    def cancellation_refunded_fa(self, obj):
        if obj.cancellation_refunded_amount > 0:
            formatted_value = "{:,}".format(int(obj.cancellation_refunded_amount))
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', formatted_value)
        return "-"

    @admin.display(description='درخواست کنسلی', boolean=True)
    def cancellation_requested_fa(self, obj):
        return obj.cancellation_requested

    @admin.display(description='وضعیت ظرفیت')
    def capacity_status_colored(self, obj):
        colors = {'confirmed': 'green', 'rejected': 'red', 'pending': 'orange'}
        color = colors.get(obj.capacity_status, 'gray')
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_capacity_status_display()
        )

    @admin.display(description='وضعیت پرداخت')
    def payment_status_colored(self, obj):
        colors = {'paid': 'green', 'unpaid': 'red', 'pending': 'orange'}
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_payment_status_display()
        )

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
                obj.total_half_day_charge = total_half
                obj.final_price = final_price
                obj._skip_price_calculation = True
                obj.save(update_fields=[
                    'total_price', 'total_extra_passenger_charge', 'discount',
                    'room_fixed_discount', 'half_day_in_charge',
                    'half_day_out_charge', 'total_half_day_charge', 'final_price'
                ])


# ==============================================================================
# بخش ۹: کنسلی‌ها و تنظیمات سیستمی
# ==============================================================================

@admin.register(UserCancellation)
class UserCancellationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reservation_tracking_code',
        'penalty_type',
        'penalty_value',
        'status',
        'created_jalali',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('reservation__tracking_code', 'description')
    autocomplete_fields = ('reservation',)
    filter_horizontal = ('reasons',)
    readonly_fields = ('created_jalali', 'updated_jalali')

    fieldsets = (
        (None, {
            'fields': ('reservation', 'reasons', 'description', 'status', 'penalty_type', 'penalty_value')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_jalali', 'updated_jalali')
        }),
    )

    def reservation_tracking_code(self, obj):
        return obj.reservation.tracking_code if obj.reservation else '-'
    reservation_tracking_code.short_description = 'کد پیگیری رزرو'

    @admin.display(description=_('تاریخ ثبت'))
    def created_jalali(self, obj):
        if obj.created_at:
            dt = obj.created_at.togregorian() if hasattr(obj.created_at, 'togregorian') else obj.created_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M')
        return '-'

    @admin.display(description=_('تاریخ بررسی'))
    def updated_jalali(self, obj):
        if obj.updated_at:
            dt = obj.updated_at.togregorian() if hasattr(obj.updated_at, 'togregorian') else obj.updated_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M')
        return '-'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status == 'approved':
            try:
                result = obj.process_cancellation()
                messages.success(
                    request,
                    f"کنسلی پردازش شد. جریمه: {result['penalty_amount']:,} تومان | برگشت به کیف‌پول: {result['refund_amount']:,} تومان"
                )
            except Exception as e:
                messages.error(request, f"خطا در پردازش کنسلی: {e}")


@admin.register(ReservationInvoiceSettings)
class ReservationInvoiceSettingsAdmin(admin.ModelAdmin):
    form = ReservationInvoiceSettingsAdminForm
    list_display = ('title', 'contact_number_1', 'contact_number_2', 'signature_preview_list')
    search_fields = ('title', 'contact_number_1', 'contact_number_2')

    def signature_preview_list(self, obj):
        if obj.signature_image:
            return format_html('<img src="{}" style="max-height: 35px; border-radius: 4px;" />', obj.signature_image.url)
        return "-"
    signature_preview_list.short_description = "امضا"

    def has_add_permission(self, request):
        return not ReservationInvoiceSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SnappTripSetting)
class SnappTripSettingAdmin(admin.ModelAdmin):
    list_display = ('title', 'base_url', 'is_active', 'has_api_key', 'wallet_balance_display')
    fieldsets = (
        ('اطلاعات احراز هویت وب‌سرویس اسنپ‌تریپ', {
            'fields': ('title', 'base_url', 'swagger_url', 'api_key', 'is_active'),
        }),
    )

    def has_api_key(self, obj):
        return bool(obj.api_key)
    has_api_key.boolean = True
    has_api_key.short_description = "کلید ثبت شده؟"

    @admin.display(description="موجودی کیف‌پول اسنپ")
    def wallet_balance_display(self, obj):
        try:
            bal, status_msg = get_snapptrip_wallet_balance()
            bal_int = int(bal or 0)
            if bal_int > 0:
                return format_html('<strong style="color: #28a745;">{} تومان</strong>', f"{bal_int:,}")
            elif bal_int == 0 and status_msg == "موفق":
                return format_html('<span style="color: #dc3545;">۰ تومان (کیف‌پول خالی است)</span>')
            return format_html('<span style="color: #6c757d;">{}</span>', str(status_msg)[:40])
        except Exception as e:
            return format_html('<span style="color: red;">خطا: {}</span>', str(e)[:30])

    def has_add_permission(self, request):
        return not SnappTripSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SnappHotelDirectory)
class SnappHotelDirectoryAdmin(admin.ModelAdmin):
    list_display = ('snapp_hotel_id', 'name', 'city_display', 'stars_display', 'last_synced_jalali')
    search_fields = ('snapp_hotel_id', 'name', 'city_name', 'city_id')
    list_filter = ('stars', 'city_name')
    readonly_fields = ('snapp_hotel_id', 'name', 'city_name', 'city_id', 'last_synced')
    actions = ['trigger_sync_action', 'auto_detect_stars_action']
    list_per_page = 50

    @admin.display(description="شهر", ordering="city_name")
    def city_display(self, obj):
        return obj.city_name or str(obj.city_id or "-")

    @admin.display(description="تعداد ستاره", ordering="stars")
    def stars_display(self, obj):
        val = str(obj.stars or '').strip()
        fa_to_en = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        val_clean = val.translate(fa_to_en).replace('.0', '').strip()

        if val_clean in ['1', '2', '3', '4', '5']:
            star_num = int(val_clean)
            gold_stars = "★" * star_num
            gray_stars = "☆" * (5 - star_num)
            return format_html(
                '<span style="color: #f39c12; font-size: 14px;">{}</span>'
                '<span style="color: #ccc; font-size: 14px;">{}</span>',
                gold_stars, gray_stars
            )
        return format_html('<span style="background: #f1f3f5; color: #495057; padding: 2px 6px; border-radius: 4px; font-size: 11px;">مهمان‌پذیر / بوم‌گردی</span>')

    def last_synced_jalali(self, obj):
        if obj.last_synced:
            dt = obj.last_synced.togregorian() if hasattr(obj.last_synced, 'togregorian') else obj.last_synced
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M')
        return '-'
    last_synced_jalali.short_description = "تاریخ بروزرسانی"

    @admin.action(description="🔄 بروزرسانی بانک هتل‌ها از سرور اسنپ‌تریپ")
    def trigger_sync_action(self, request, queryset):
        success, msg = sync_all_snapptrip_hotels_directory()
        if success:
            self.message_user(request, msg, messages.SUCCESS)
        else:
            self.message_user(request, msg, messages.ERROR)

    @admin.action(description="⭐ استخراج و ثبت خودکار ستاره‌ها از نام هتل‌ها")
    def auto_detect_stars_action(self, request, queryset):
        count = 0
        star_patterns = [
            ('5', ['۵ ستاره', '5 ستاره', 'پنج ستاره']),
            ('4', ['۴ ستاره', '4 ستاره', 'چهار ستاره']),
            ('3', ['۳ ستاره', '3 ستاره', 'سه ستاره']),
            ('2', ['۲ ستاره', '2 ستاره', 'دو ستاره']),
            ('1', ['۱ ستاره', '1 ستاره', 'یک ستاره']),
        ]
        for hotel in queryset:
            name = hotel.name or ""
            for s_val, s_words in star_patterns:
                if any(w in name for w in s_words):
                    if hotel.stars != s_val:
                        hotel.stars = s_val
                        hotel.save(update_fields=['stars'])
                        count += 1
                    break
        self.message_user(request, f"تعداد {count} هتل با موفقیت ستاره‌دار شدند.", messages.SUCCESS)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-all-snapp-hotels/', self.admin_site.admin_view(self.sync_all_view), name='sync-all-snapp-hotels'),
        ]
        return custom_urls + urls

    def sync_all_view(self, request):
        success, msg = sync_all_snapptrip_hotels_directory()
        if success:
            self.message_user(request, msg, messages.SUCCESS)
        else:
            self.message_user(request, msg, messages.ERROR)
        return redirect(reverse('admin:reservation_snapphoteldirectory_changelist'))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = format_html(
            '{} &nbsp;&nbsp; <a class="button" style="background:#007bff; color:white; padding:5px 12px; border-radius:4px; font-size:13px; text-decoration:none;" href="{}">🔄 بروزرسانی بانک هتل‌ها از اسنپ</a>',
            "بانک هتل‌های اسنپ‌تریپ",
            reverse('admin:sync-all-snapp-hotels')
        )
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False