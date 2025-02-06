from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
    SiteConfig,
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

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'sub_title',
        'page',
    )
    search_fields = (
        'title',
        'sub_title',
        'page',
    )

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    def header_logo_preview(self, obj):
        return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.header_logo.url) if obj.header_logo else ''
    def footer_logo_preview(self, obj):
        return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.footer_logo.url) if obj.footer_logo else ''

    header_logo_preview.short_description = 'لوگوی هدر'
    footer_logo_preview.short_description = 'لوگوی فوتر'
    readonly_fields = (
        'header_logo_preview',
        'footer_logo_preview',
    )

    fieldsets = (
        (None, {
            'fields': (
                'header_title',
                'header_sub_title',
                'header_logo',
                'header_logo_preview',
                'footer_title',
                'footer_logo',
                'footer_logo_preview',
                'footer_description',
            )
        }),
    )
    list_display = (
        'id',
        'header_logo',
        'header_title',
        'header_sub_title',
        'footer_title',
    )
    def save_model(self, request, obj, form, change):
        if not change and SiteConfig.objects.exists():
            messages.error(request, 'تنها یک کانفیگ برای سایت میتوان ساخت')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()
