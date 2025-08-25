from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import FavoriteCollection, Favorite

# تنظیمات برای مدل User
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    search_fields = ['username', 'email', 'first_name', 'last_name']

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
        'created',
    )