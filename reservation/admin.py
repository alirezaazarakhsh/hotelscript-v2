from django.contrib import admin
from django.utils.html import format_html
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
                '<img src="{}" width="40" height="40" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.best_logo.image_logo_hotel.url,
                obj.best_logo.title_logo
            )
        return "-"
    logo_preview.short_description = "لوگو انتخاب‌شده"
    

@admin.register(HotelGallery)
class HotelGalleryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )

@admin.register(HotelGalleryImage)
class HotelGalleryImageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'gallery',
    )
    search_fields = (
        'title',
    )

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
    )
    search_fields = (
        'question',
    )

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'hotel',
        'text',
        'strengths',
        'weaknesses',
        'is_approved',
        'created',
    )
    search_fields = (
        'text',
        'strengths',
        'weaknesses',
    )
    list_filter = (
        'is_approved',
    )

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