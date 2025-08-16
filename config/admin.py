import json
import os
import zipfile
import io
import logging
from click import File
from django import apps
from django.contrib import admin
from django.db import transaction, IntegrityError
from django.dispatch import receiver
from django.forms import TextInput   
from django.utils.html import mark_safe
from django.http import HttpResponse
from colorfield.widgets import ColorWidget
from django.utils.html import format_html
from colorfield.fields import ColorField
from django.db.models.signals import post_delete
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.core.files.storage import default_storage


from django.conf import settings
import jdatetime

from reservation import models
from .models import (
    AppRestore, LegalProfileSubmissionRule, Location, Page, HeaderMenu, QuickAccess, SiteConfig, Slide,
    Statistic, StatisticItem, ChooseReason, FAQ, Service, ContactInfo,
    SocialMedia, Banner, EnamadLicense, License, Advantage, FakeComment,
    Rule, ComingSoon, UserLevel, 
)
from .forms import (
    AppRestoreAdminForm, SiteConfigAdminForm, SlideAdminForm, ChooseReasonForm, ServiceForm,
    BannerForm, LicenseForm, FakeCommentForm, ComingSoonAdminForm,
    StatisticAdminForm, 
)





@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'page', 'path')
    search_fields = ('title', 'page', 'path')

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json', 'export_all_as_json']

    def export_as_json(self, request, queryset):
        """بکاپ از رکوردهای انتخاب شده"""
        return self._export_json(queryset, filename='pages_backup.json')

    def export_all_as_json(self, request, queryset=None):
        """بکاپ از تمام رکوردها"""
        all_objs = Page.objects.all()
        return self._export_json(all_objs, filename='pages_backup_all.json')

    def _export_json(self, queryset, filename):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'page': obj.page,
                'path': obj.path,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"
    export_all_as_json.short_description = "بکاپ JSON از تمام داده‌های Page"






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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'order': obj.order,
                'title': obj.title,
                'page': obj.page.id if obj.page else None,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=headermenu_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'order': obj.order,
                'title': obj.title,
                'page': obj.page.id if obj.page else None,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=quickaccess_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'header_title': obj.header_title,
                'header_sub_title': obj.header_sub_title,
                'footer_title': obj.footer_title,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=siteconfig_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    form = SlideAdminForm
    list_display = ('id', 'order')

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'order': obj.order,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=slides_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            items = []
            for item in obj.statisticitem_set.all():
                items.append({
                    'id': item.id,
                    'title': item.title,
                    'value': item.value,
                })

            data.append({
                'id': obj.id,
                'title': obj.title,
                'description': obj.description,
                'items': items,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=statistics_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(ChooseReason)
class ChooseReasonAdmin(admin.ModelAdmin):
    form = ChooseReasonForm
    list_display = ('id', 'title', 'description')

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'description': obj.description,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=choose_reason_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"




@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'icon_preview', 'page')
    search_fields = ('question', 'answer', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

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

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'question': obj.question,
                'answer': obj.answer,
                'icon': obj.icon.id if obj.icon else None,
                'page': obj.page.id if obj.page else None,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=faq_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    form = ServiceForm
    list_display = ('id', 'title', 'description')
    search_fields = ('title', 'description')

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'description': obj.description,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=service_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'subtitle': obj.subtitle,
                'value': obj.value,
                'link': obj.link,
                'show_in_footer': obj.show_in_footer,
                'icon': obj.icon.id if obj.icon else None,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=contactinfo_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'type': obj.type,
                'type_fa': obj.type_fa,
                'link': obj.link,
                'show_in_footer': obj.show_in_footer,
                'icon': obj.icon.id if obj.icon else None,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=socialmedia_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerForm
    list_display = ('id', 'page', 'order', 'title', 'link')
    search_fields = ('title', 'link')
    list_filter = ('page',)

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'page': obj.page.id if obj.page else None,
                'order': obj.order,
                'title': obj.title,
                'link': obj.link,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=banners_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=enamad_licenses_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    form = LicenseForm
    list_display = ('id', 'link')
    search_fields = ('link',)

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'link': obj.link,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=licenses_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'subtitle': obj.subtitle,
                'icon': obj.icon.id if obj.icon else None,
            })
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=advantages_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"






@admin.register(FakeComment)
class FakeCommentAdmin(admin.ModelAdmin):
    form = FakeCommentForm
    list_display = ('id', 'commenter', 'evaluation', 'text', 'rate')
    search_fields = ('commenter', 'text')

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse

        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'commenter': obj.commenter,
                'evaluation': obj.evaluation,
                'text': obj.text,
                'rate': obj.rate,
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=fake_comments_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"





@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'tab_title', 'order')
    list_editable = ('order',)
    search_fields = ('tab_title', 'text')
    ordering = ('order',)

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'tab_title': obj.tab_title,
                'text': obj.text,
                'order': obj.order,
            })
        from django.http import HttpResponse
        import json
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=rules_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"




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

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'subtitle': obj.subtitle,
                'end_date': obj.end_date.isoformat() if obj.end_date else None,
                'copyright_text': obj.copyright_text,
                'is_active': obj.is_active,
            })
        from django.http import HttpResponse
        import json
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=comingsoon_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"




@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'color_preview', 'icon_preview')
    search_fields = ('title', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    # استفاده از Color Picker برای فیلد color
    formfield_overrides = {
        ColorField: {'widget': ColorWidget},
    }

    def save_model(self, request, obj, form, change):
        if not change and UserLevel.objects.count() >= 3:
            self.message_user(request, 'شما نمی‌توانید بیشتر از ۳ سطح کاربری بسازید.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # محدودیت ۳ سطح کاربری
        return UserLevel.objects.count() < 3

    def icon_preview(self, obj):
        if obj.icon and getattr(obj.icon, 'svg_icon', None):
            return mark_safe(
                f'<div style="display:flex;align-items:center;">'
                f'<img src="{obj.icon.svg_icon.url}" width="30" height="30" '
                f'style="margin-right:8px; object-fit: contain;" />'
                f'<span>{obj.icon.title_icon}</span>'
                f'</div>'
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"

    def color_preview(self, obj):
        if obj.color:
            return format_html(
                '<div style="width:30px; height:30px; background-color:{}; border:1px solid #000;"></div>',
                obj.color
            )
        return "-"
    color_preview.short_description = "پیش‌نمایش رنگ"

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'title': obj.title,
                'color': obj.color,
                'icon': obj.icon.id if obj.icon else None,
            })
        from django.http import HttpResponse
        import json
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=userlevels_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"

    
    
    

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'latitude', 'longitude')
    search_fields = ('latitude', 'longitude')

    def save_model(self, request, obj, form, change):
        if not change and Location.objects.exists():
            self.message_user(request, 'تنها یک کانفیگ تماس با ما می‌توان ساخت.', level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not Location.objects.exists()

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'latitude': obj.latitude,
                'longitude': obj.longitude,
            })
        from django.http import HttpResponse
        import json
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=locations_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"

    
    
    
@admin.register(LegalProfileSubmissionRule)
class LegalProfileSubmissionRuleAdmin(admin.ModelAdmin):
    list_display = ['description']
    search_fields = ['description']
    
    def has_add_permission(self, request):
        # جلوگیری از افزودن نمونه جدید اگر یکی وجود داشته باشد
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return True

    # =======================
    # اکشن بکاپ JSON
    # =======================
    actions = ['export_as_json']

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append({
                'id': obj.id,
                'description': obj.description,
            })
        from django.http import HttpResponse
        import json
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename=legal_profile_submission_rules_backup.json'
        return response

    export_as_json.short_description = "بکاپ JSON از داده‌های انتخاب شده"

    



# ادمین ریستور
@admin.register(AppRestore)
class AppRestoreAdmin(admin.ModelAdmin):
    form = AppRestoreAdminForm
    list_display = ('id', 'restored_apps', 'created_at_jalali')
    filter_horizontal = ('apps',)

    def restored_apps(self, obj):
        return ", ".join([f"{app.app_label} | {app.model}" for app in obj.apps.all()])
    restored_apps.short_description = "اپلیکیشن‌های ریستور شده"

    def created_at_jalali(self, obj):
        if obj.created_at:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jalali_date.strftime('%Y/%m/%d %H:%M')
        return "-"
    created_at_jalali.short_description = "تاریخ ریستور (شمسی)"

    def save_model(self, request, obj, form, change):
        # ابتدا instance را ذخیره کن
        super().save_model(request, obj, form, change)

        # ست کردن مقدار انتخاب‌شده‌ی apps
        if form.cleaned_data.get('apps'):
            obj.apps.set(form.cleaned_data['apps'])
            obj.save()

        # بررسی فایل JSON
        if not obj.backup_json:
            self.message_user(request, "هیچ فایلی برای ریستور انتخاب نشده.", level='warning')
            return

        try:
            with obj.backup_json.open('rb') as f:
                content = f.read().decode('utf-8')
                data = json.loads(content)
                self.message_user(request, "داده‌های JSON خوانده شد.", level='info')
        except Exception as e:
            self.message_user(request, f"خطا در خواندن فایل JSON: {e}", level='error')
            return

        if not obj.apps.exists():
            self.message_user(request, "هیچ اپلیکیشنی انتخاب نشده است!", level='error')
            return

        self.message_user(
            request,
            f"اپلیکیشن‌های انتخاب‌شده: {[f'{app.app_label} | {app.model}' for app in obj.apps.all()]}",
            level='info'
        )

        # ریستور داده‌ها در تراکنش اتمیک
        with transaction.atomic():
            for app_content in obj.apps.all():
                app_label = app_content.app_label
                model_name = app_content.model
                self.message_user(request, f"پردازش مدل: {model_name} از اپ {app_label}", level='info')

                try:
                    model_class = apps.get_model(app_label, model_name)
                except LookupError:
                    self.message_user(request, f"مدل {model_name} در اپ {app_label} پیدا نشد.", level='error')
                    continue

                # پیدا کردن رکوردهای مربوط به مدل
                if isinstance(data, dict):
                    records = data.get(model_name, [])
                elif isinstance(data, list):
                    records = data
                else:
                    records = []

                if not records:
                    self.message_user(request, f"هیچ داده‌ای برای مدل {model_name} یافت نشد.", level='warning')
                    continue

                # حذف داده‌های قبلی
                model_class.objects.all().delete()
                self.message_user(request, f"داده‌های قبلی مدل {model_name} حذف شدند.", level='info')

                # ایجاد رکوردهای جدید
                for record in records:
                    new_obj = model_class()
                    for field_name, value in record.items():
                        try:
                            field = model_class._meta.get_field(field_name)
                            # ForeignKey
                            if field.many_to_one and value is not None:
                                related_model = field.remote_field.model
                                try:
                                    related_instance = related_model.objects.get(id=value)
                                    setattr(new_obj, field_name, related_instance)
                                except related_model.DoesNotExist:
                                    self.message_user(
                                        request,
                                        f"ForeignKey {field_name} با id={value} در مدل {related_model.__name__} موجود نیست! مقدار پیش‌فرض NULL ست شد.",
                                        level='warning'
                                    )
                                    setattr(new_obj, field_name, None)
                            # ImageField
                            elif field.get_internal_type() == 'ImageField' and value:
                                if default_storage.exists(value):
                                    with default_storage.open(value, 'rb') as f_img:
                                        new_obj.__dict__[field_name] = File(f_img, name=os.path.basename(value))
                                else:
                                    self.message_user(request, f"فایل تصویر {value} موجود نیست!", level='warning')
                            # سایر فیلدها
                            else:
                                setattr(new_obj, field_name, value)
                        except Exception as e:
                            self.message_user(request, f"خطا در پر کردن فیلد {field_name}: {e}", level='error')

                    # قبل از ذخیره بررسی فیلدهای NOT NULL
                    for field in model_class._meta.fields:
                        if not field.null and getattr(new_obj, field.name) is None:
                            if field.many_to_one:
                                setattr(new_obj, field.name, None)
                            elif field.get_internal_type() in ['CharField', 'TextField']:
                                setattr(new_obj, field.name, '')

                    try:
                        new_obj.save()
                        self.message_user(request, f"رکورد {new_obj} برای مدل {model_name} ایجاد شد.", level='info')
                    except IntegrityError as e:
                        self.message_user(request, f"خطای IntegrityError در ذخیره رکورد {model_name}: {e}", level='error')
                        raise
                    except Exception as e:
                        self.message_user(request, f"خطا در ذخیره رکورد {model_name}: {e}", level='error')
                        raise

        self.message_user(request, "ریستور با موفقیت انجام شد!", level='success')
