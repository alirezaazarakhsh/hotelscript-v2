import logging
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
import jdatetime
from authentication import forms
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
    ReservationRoom,
    ReservationRoomPassenger,
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
    SuggestedCommentItem,
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


class HotelTagPublicInline(admin.TabularInline):
    model = HotelTagPublic
    extra = 0  # No extra empty forms by default
    max_num = 3  # Maximum of 5 tags
    fields = ('title',)
    verbose_name = _('تگ عمومی')
    verbose_name_plural = _('تگ‌های عمومی')

# Updated HotelAdmin class
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm

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
    search_fields = (
        'name',
        'address',
        'public_tags__title',  # Enable searching by public tag titles
    )
    autocomplete_fields = ['tags', 'facilities', 'room_facilities', 'best_logo']
    readonly_fields = ('logo_preview',)
    inlines = [HotelTagPublicInline]  # Add the inline

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

    def show_public_tags(self, obj):
        qs = obj.public_tags.all()  # Access public_tags related_name
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
    
    

logger = logging.getLogger(__name__)

# ---------------- Passenger Inline ----------------
class ReservationRoomPassengerInline(admin.TabularInline):
    model = ReservationRoomPassenger
    extra = 0
    max_num = 8
    fields = ('passenger_type', 'first_name', 'last_name', 'mobile_number', 'national_code')
    can_delete = True
    autocomplete_fields = ()

# ---------------- Room Inline ----------------
class ReservationRoomInline(admin.TabularInline):
    model = ReservationRoom
    extra = 0
    max_num = 3
    fields = ('room',)
    autocomplete_fields = ('room',)
    show_change_link = True
    can_delete = True

# ---------------- Reservationhotel Admin ----------------
@admin.register(Reservationhotel)
class ReservationhotelAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_code', 'buyer', 'reserver_first_name', 'reserver_last_name',
        'reserver_phone_number', 'check_in_date', 'check_out_date',
        'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'final_price', 'status', 'created_jalali'
    )
    search_fields = (
        'tracking_code', 'buyer__phone_number', 'reserver_first_name',
        'reserver_last_name', 'reserver_phone_number', 'reserver_national_code'
    )
    list_filter = ('status', 'check_in_date', 'check_out_date')
    autocomplete_fields = ('buyer',)
    inlines = [ReservationRoomInline]  # فقط اتاق‌ها

    readonly_fields = (
        'tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'created_jalali', 'updated_jalali', 'final_price'
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
            'fields': ('total_price', 'discount', 'final_price', 'status')
        }),
        (_('اطلاعات سیستم'), {
            'fields': ('tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
                       'created_jalali', 'updated_jalali')
        }),
    )

    def created_jalali(self, obj):
        if obj.created_at:
            return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    created_jalali.short_description = 'تاریخ ایجاد (شمسی)'

    def updated_jalali(self, obj):
        if obj.updated_at:
            return jdatetime.datetime.fromgregorian(datetime=obj.updated_at).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    updated_jalali.short_description = 'تاریخ به‌روزرسانی (شمسی)'

    def nights_count_fa(self, obj):
        return obj.nights_count if obj.pk else 0
    nights_count_fa.short_description = 'تعداد شب‌ها'

    def total_rooms_fa(self, obj):
        return obj.total_rooms if obj.pk else 0
    total_rooms_fa.short_description = 'کل اتاق‌ها'

    def total_guests_fa(self, obj):
        return obj.total_guests if obj.pk else 0
    total_guests_fa.short_description = 'کل مهمان‌ها'

# ---------------- ReservationRoom Admin ----------------
@admin.register(ReservationRoom)
class ReservationRoomAdmin(admin.ModelAdmin):
    list_display = ('room', 'reservation_display')
    search_fields = ('room__title', 'reservation__tracking_code')
    autocomplete_fields = ('room', 'reservation')
    inlines = [ReservationRoomPassengerInline]  # Inline مسافران زیر هر اتاق

    def reservation_display(self, obj):
        return obj.reservation.tracking_code
    reservation_display.short_description = 'رزرو'

