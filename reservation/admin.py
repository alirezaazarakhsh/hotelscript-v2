from django.contrib import admin
from .models import (
    Province,
    City,
    HotelType,
    HotelTag,
    Facilities,
    RoomFacilities,
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
