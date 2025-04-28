from django.contrib import admin
from .models import (
    Province,
    City,
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
