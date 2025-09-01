import os
import logging
from django.contrib import admin
from django.forms import TextInput   
from django.utils.html import mark_safe, format_html
from colorfield.widgets import ColorWidget
from colorfield.fields import ColorField

from reservation import models
from .models import (
    LegalProfileSubmissionRule, Location, Page, HeaderMenu, QuickAccess, SiteConfig, Slide,
    Statistic, StatisticItem, ChooseReason, FAQ, Service, ContactInfo,
    SocialMedia, Banner, EnamadLicense, License, Advantage, FakeComment,
    Rule, ComingSoon, UserLevel, 
)
from .forms import (
    SiteConfigAdminForm, SlideAdminForm, ChooseReasonForm, ServiceForm,
    BannerForm, LicenseForm, FakeCommentForm, ComingSoonAdminForm,
    StatisticAdminForm, 
)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'page', 'path')
    search_fields = ('title', 'page', 'path')


@admin.register(HeaderMenu)
class HeaderMenuAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    def save_model(self, request, obj, form, change):
        max_count = getattr(HeaderMenu, 'MAX_ALLOWED_INSTANCES', 5)
        if not change and HeaderMenu.objects.count() >= max_count:
            self.message_user(request, f'تنها به تعداد {max_count} منوی هدر می‌توانید بسازید.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        max_count = getattr(HeaderMenu, 'MAX_ALLOWED_INSTANCES', 5)
        return HeaderMenu.objects.count() < max_count


@admin.register(QuickAccess)
class QuickAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    def save_model(self, request, obj, form, change):
        max_count = getattr(QuickAccess, 'MAX_ALLOWED_INSTANCES', 5)
        if not change and QuickAccess.objects.count() >= max_count:
            self.message_user(request, f'تنها به تعداد {max_count} دسترسی سریع می‌توانید بسازید.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        max_count = getattr(QuickAccess, 'MAX_ALLOWED_INSTANCES', 5)
        return QuickAccess.objects.count() < max_count


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    form = SiteConfigAdminForm
    list_display = ('id', 'header_title', 'header_sub_title', 'footer_title')

    def save_model(self, request, obj, form, change):
        if not change and SiteConfig.objects.exists():
            self.message_user(request, 'تنها یک کانفیگ برای سایت می‌توان ساخت', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    form = SlideAdminForm
    list_display = ('id', 'order', 'image_preview')
    search_fields = ('order',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:100px;"/>', obj.image.url)
        return "-"
    image_preview.short_description = "پیش‌نمایش تصویر"


class StatisticItemInline(admin.TabularInline):
    model = StatisticItem
    extra = 4

    def get_max_num(self, request, obj=None, **kwargs):
        return 4


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    form = StatisticAdminForm
    list_display = ('id', 'title', 'description')
    inlines = [StatisticItemInline]

    def save_model(self, request, obj, form, change):
        if not change and Statistic.objects.exists():
            self.message_user(request, 'تنها یک کانفیگ درباره ما می‌توان ساخت.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not Statistic.objects.exists()


@admin.register(ChooseReason)
class ChooseReasonAdmin(admin.ModelAdmin):
    form = ChooseReasonForm
    list_display = ('id', 'title', 'description')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'icon_preview', 'page')
    search_fields = ('question', 'answer', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" style="margin-right:8px;" />'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    form = ServiceForm
    list_display = ('id', 'title', 'description')
    search_fields = ('title', 'description')


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'value', 'link', 'show_in_footer', 'icon_preview')
    search_fields = ('title', 'subtitle', 'value', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    def icon_preview(self, obj):
        if obj.icon and getattr(obj.icon, 'svg_icon', None):
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


@admin.register(SocialMedia)
class SocialMediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'type_fa', 'link', 'show_in_footer', 'icon_preview')
    search_fields = ('type', 'type_fa', 'link', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    def icon_preview(self, obj):
        if obj.icon and getattr(obj.icon, 'svg_icon', None):
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerForm
    list_display = ('id', 'page', 'order', 'title', 'link')
    search_fields = ('title', 'link')
    list_filter = ('page',)


@admin.register(EnamadLicense)
class EnamadLicenseAdmin(admin.ModelAdmin):
    list_display = ('id',)

    def save_model(self, request, obj, form, change):
        if not change and EnamadLicense.objects.exists():
            self.message_user(request, 'تنها یک کد اینماد می‌توان ساخت', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not EnamadLicense.objects.exists()


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    form = LicenseForm
    list_display = ('id', 'link')
    search_fields = ('link',)


@admin.register(Advantage)
class AdvantageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'icon_preview')
    search_fields = ('title', 'subtitle', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"

    def has_add_permission(self, request):
        max_advantages = 4
        if Advantage.objects.count() >= max_advantages:
            return False
        return super().has_add_permission(request)


@admin.register(FakeComment)
class FakeCommentAdmin(admin.ModelAdmin):
    form = FakeCommentForm
    list_display = ('id', 'commenter', 'evaluation', 'text', 'rate')
    search_fields = ('commenter', 'text')


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'tab_title', 'order')
    list_editable = ('order',)
    search_fields = ('tab_title', 'text')
    ordering = ('order',)


@admin.register(ComingSoon)
class ComingSoonAdmin(admin.ModelAdmin):
    form = ComingSoonAdminForm
    list_display = ('id', 'title', 'subtitle', 'end_date', 'copyright_text', 'is_active')

    def save_model(self, request, obj, form, change):
        if not change and ComingSoon.objects.exists():
            self.message_user(request, 'تنها یک کامینگ سون می‌توان ساخت', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not ComingSoon.objects.exists()


@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'color_preview', 'icon_preview')
    search_fields = ('title', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    formfield_overrides = {
        ColorField: {'widget': ColorWidget},
    }

    def save_model(self, request, obj, form, change):
        if not change and UserLevel.objects.count() >= 3:
            self.message_user(request, 'شما نمی‌توانید بیشتر از ۳ سطح کاربری بسازید.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def color_preview(self, obj):
        if obj.color:
            return format_html(
                '<div style="width:30px; height:30px; background-color:{}; border:1px solid #000;"></div>',
                obj.color
            )
        return "-"
    color_preview.short_description = "رنگ"

    def icon_preview(self, obj):
        if obj.icon and getattr(obj.icon, 'svg_icon', None):
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" style="margin-right:8px;"/>'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"
