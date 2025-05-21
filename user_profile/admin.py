from django.contrib import admin
from .models import (
    FavoriteCollection,
    Favorite,
    CustomerClub,
    CustomerClubPrize,
)

# Register your models here.
@admin.register(FavoriteCollection)
class FavoriteCollectionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'title',
    )

    search_fields = (
        'title',
    )

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'item',
        'created',
    )

@admin.register(CustomerClub)
class CustomerClubAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'points',
    )

@admin.register(CustomerClubPrize)
class CustomerClubPrizeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'type',
        'required_points',
        'expired_date',
        'discount_code',
    )

    search_fields = (
        'title',
    )
