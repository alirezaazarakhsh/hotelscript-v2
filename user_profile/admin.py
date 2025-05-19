from django.contrib import admin
from .models import (
    FavoriteCollection,
    Favorite,
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
