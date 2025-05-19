from django.contrib import admin
from .models import (
    FavoriteCollection,
    Favorite,
)

# Register your models here.
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'item',
        'created',
    )

@admin.register(FavoriteCollection)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'title',
    )

    search_fields = (
        'title',
    )
