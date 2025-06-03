from django.contrib import admin
from django.utils.html import format_html
from .models import IconShortcut

@admin.register(IconShortcut)
class IconShortcutAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'title_icon',
        'svg_icon_preview',
    )
    search_fields = (
        'title_icon',
    )
    ordering = ('order',)

    readonly_fields = ('svg_icon_preview',)

    def svg_icon_preview(self, obj):
        if obj.svg_icon:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: contain;" />',
                obj.svg_icon.url
            )
        return "-"
    svg_icon_preview.short_description = "پیش‌نمایش آیکون"
