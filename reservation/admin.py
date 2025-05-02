from django.contrib import admin
from .models import (
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
    list_display = (
        'id',
        'name',
        'slug',
        'province',
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
        'slug',
    )
    search_fields = (
        'title',
        'slug',
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
    list_display = (
        'id',
        'name',
        'slug',
        'city',
        'address',
        'stars',
        'type',
        'floors_count',
        'latitude',
        'longitude',
    )
    search_fields = (
        'name',
        'address',
    )

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
        'is_preferred',
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

@admin.register(RoomDate)
class RoomDateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'room',
        'date',
        'price',
        'extra_passenger_price',
        'foreign_passenger_price',
        'discount',
    )
    search_fields = (
        'room',
        'date',
    )

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
