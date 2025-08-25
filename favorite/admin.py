from django.contrib import admin
from .models import FavoriteCollection, Favorite

# ثبت مدل‌های FavoriteCollection و Favorite
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
    autocomplete_fields = ['user']

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'item',
    )
