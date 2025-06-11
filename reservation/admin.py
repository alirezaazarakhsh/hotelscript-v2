from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from reservation.forms import BestHotelsAdminForm, CityAdminForm,  HotelAdminForm
from .models import (
    BestHotels,
    ClosedDate,
    Province,
    City,
    HotelType,
    HotelTag,
    Facilities,
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
    RoomDateDiscount,
    RoomDate,
    Passenger,
    Reservation,
)

# Register your models here.
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
            return format_html('<img src="{}" width="100" style="object-fit: cover; border: 1px solid #ccc; border-radius: 4px;" />', obj.image.url)
        return "-"
    preview.short_description = 'پیش‌نمایش'


@admin.register(HotelGallery)
class HotelGalleryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'hotel')
    search_fields = ('title', 'hotel__name')
    autocomplete_fields = ['hotel']  # ✅ انتخاب هتل با قابلیت جستجو
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
        'icon_preview',  # به جای 'icon' که فقط متن بود، نمایش تصویر گذاشتیم
    )
    search_fields = (
        'question',
        'hotel__title',   # اگر می‌خوای سرچ روی نام هتل هم داشته باشی
        'icon__title_icon',  # سرچ روی عنوان آیکون هم اضافه کردم
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
        'created_jalali',  # تاریخ شمسی بجای created میلادی
    )
    search_fields = (
        'text',
        'strengths__title',  # چون ManyToManyField هست و به CommentPointItem رفرنس میده
        'weaknesses__title',
    )
    list_filter = (
        'is_approved',
        'stars',
    )

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
        return obj.created_jalali
    created_jalali.admin_order_field = 'created'  # امکان مرتب سازی بر اساس created میلادی
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

@admin.register(CommentPoint)
class CommentPointAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'comment',
        'comment_point_item',
        'point',
    )
    search_fields = (
        'comment',
    )

@admin.register(RoomService)
class RoomServiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hotel',
        'title',
        'capacity',
        'extra_capacity',
        'customer_club_points',
        'count',
        'auto_approved_count',
    )
    search_fields = (
        'title',
    )

@admin.register(RoomDateDiscount)
class RoomDateDiscountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'type',
        'value',
        'maximum_value',
        'start_date',
        'end_date',
        'count',
    )


class ClosedDateInline(admin.TabularInline):
    model = ClosedDate
    extra = 1

@admin.register(RoomDate)
class RoomDateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'room',
        'jalali_date',
        'jalali_dateend',
        'price',
        'extra_passenger_price',
        'foreign_passenger_price',
        'discount',
    )
    search_fields = (
        'room__title',
        'date',
    )
    inlines = [ClosedDateInline]  # اضافه کردن اینلاین اینجا
    


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