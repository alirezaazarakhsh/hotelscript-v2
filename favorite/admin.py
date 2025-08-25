from django.contrib import admin
from django.contrib.auth.models import User
from .models import FavoriteCollection, Favorite

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
    autocomplete_fields = ['user']

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'item',
        'created',
    )

# تنظیم جستجو برای مدل User
admin.site.unregister(User)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'email', 'first_name', 'last_name']