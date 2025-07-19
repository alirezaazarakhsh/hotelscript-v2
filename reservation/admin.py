from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from reservation.forms import BestHotelsAdminForm, CityAdminForm, HotelAdminForm
from .models import (
    BestHotels,
    ClosedDate,
    Province,
    City,
    HotelType,
    HotelTag,
    Facilities,
    ReservationApprovalDuration,
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
    Reservation,
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
    )
    search_fields = (
        'title',
    )


@admin.register(RoomFacilities)
class RoomFacilitiesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


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
        'type',
        'floors_count',
        'logo_preview',
    )
    search_fields = (
        'name',
        'address',
    )
    autocomplete_fields = ['tags', 'facilities', 'room_facilities', 'best_logo']
    readonly_fields = ('logo_preview',)

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
        return obj.current_jalali
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
    #    'show_closed_dates',
        'foreign_passenger_price',
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
                'foreign_passenger_price',
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


@admin.register(ClosedDate)
class ClosedDateAdmin(admin.ModelAdmin):
    list_display = ('room_date', 'date', 'user_level')
    list_filter = ('room_date', 'user_level')
    search_fields = ('room_date__room__name',)
    autocomplete_fields = ('room_date', 'user_level')
    ordering = ('date',)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'first_name',
        'last_name',
        'national_code',
        'phone_number',
    )
    search_fields = (
        'first_name',
        'last_name',
        'national_code',
        'phone_number',
    )


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'uuid',
        'user',
        'status',
        'created',
        'updated',
    )
    search_fields = (
        'uuid',
    )
    list_filter = (
        'status',
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