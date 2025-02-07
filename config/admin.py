from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
    SiteConfig,
    Slider,
)
from .forms import (
    SiteConfigAdminForm,
    SliderAdminForm,
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

    def save_model(self, request, obj, form, change):
        if not change and HeaderMenu.objects.count() >= HeaderMenu.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {HeaderMenu.MAX_ALLOWED_INSTANCES} منوی هدر میتوانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return HeaderMenu.objects.count() < HeaderMenu.MAX_ALLOWED_INSTANCES

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

    def save_model(self, request, obj, form, change):
        if not change and QuickAccess.objects.count() >= QuickAccess.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {QuickAccess.MAX_ALLOWED_INSTANCES} دسترسی سریع میتوانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return QuickAccess.objects.count() < QuickAccess.MAX_ALLOWED_INSTANCES

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
    form = SiteConfigAdminForm
    list_display = (
        'id',
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

@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    form = SliderAdminForm
    list_display = (
        'id',
        'order',
        'title',
        'link',
        'is_active',
    )
