from django.contrib import admin
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
)

# Register your models here.
@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'page',
        'path',
    )
    search_fields = (
        'title',
        'page',
        'path',
    )

@admin.register(HeaderMenu)
class HeaderMenuAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'title',
        'page',
    )
    search_fields = (
        'order',
        'title',
        'page',
    )

@admin.register(QuickAccess)
class QuickAccessAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'title',
        'page',
    )
    search_fields = (
        'order',
        'title',
        'page',
    )
