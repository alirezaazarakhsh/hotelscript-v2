from django.contrib import admin
from .models import (
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
