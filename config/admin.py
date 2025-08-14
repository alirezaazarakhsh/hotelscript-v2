import os
import zipfile
import io
import logging
from django.contrib import admin
from django.db import models as dj_models 
from django.forms import TextInput
from django.utils.html import mark_safe
from django.http import HttpResponse
from colorfield.widgets import ColorWidget
from django.utils.html import format_html
from django.conf import settings

from reservation import models
from .models import (
    LegalProfileSubmissionRule, Location, Page, HeaderMenu, QuickAccess, SiteConfig, Slide,
    Statistic, StatisticItem, ChooseReason, FAQ, Service, ContactInfo,
    SocialMedia, Banner, EnamadLicense, License, Advantage, FakeComment,
    Rule, ComingSoon, UserLevel, Folder, Media, MediaRestore,
)
from .forms import (
    SiteConfigAdminForm, SlideAdminForm, ChooseReasonForm, ServiceForm,
    BannerForm, LicenseForm, FakeCommentForm, ComingSoonAdminForm,
    StatisticAdminForm, MediaRestoreForm,
)

logger = logging.getLogger(__name__)

# Inline برای نمایش فایل‌های داخل پوشه‌ها
class MediaInline(admin.TabularInline):
    model = Media
    extra = 1
    fields = ['file', 'admin_file']
    readonly_fields = ['admin_file']

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'file_count')
    list_filter = ['created_at']
    search_fields = ['name']
    inlines = [MediaInline]

    def file_count(self, obj):
        return obj.media_files.count()
    file_count.short_description = "تعداد فایل‌ها"

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'folder', 'admin_file', 'file_size')
    list_filter = ['folder']
    search_fields = ['file']
    list_editable = ['folder']
    autocomplete_fields = ['folder']
    actions = ['export_as_zip']

    def admin_file(self, obj):
        if obj.file and obj.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return mark_safe(f'<img src="{obj.file.url}" width="100" style="object-fit:contain;" />')
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">{os.path.basename(obj.file.name)}</a>')
    admin_file.short_description = "پیش‌نمایش"

    def file_size(self, obj):
        if obj.file and os.path.exists(obj.file.path):
            size_bytes = os.path.getsize(obj.file.path)
            return f"{size_bytes / 1024:.2f} KB"
        return "نامشخص"
    file_size.short_description = "حجم فایل"

    def export_as_zip(self, request, queryset):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for media in queryset:
                if media.file and os.path.exists(media.file.path):
                    folder_name = media.folder.name if media.folder else 'root'
                    clean_file_name = media.file.name
                    while clean_file_name.startswith('media/'):
                        clean_file_name = clean_file_name[len('media/'):]
                    zip_path = os.path.join('media', folder_name, os.path.basename(clean_file_name))
                    logger.info(f"اضافه کردن فایل به ZIP: {zip_path}")
                    zip_file.write(media.file.path, zip_path)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="media_files.zip"'
        return response
    export_as_zip.short_description = "خروجی گرفتن از فایل‌ها به‌صورت ZIP"


logger = logging.getLogger(__name__)

@admin.register(MediaRestore)
class MediaRestoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'zip_file', 'uploaded_at')
    list_filter = ['uploaded_at']
    readonly_fields = ['uploaded_at']
    form = MediaRestoreForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            with zipfile.ZipFile(obj.zip_file.path, 'r') as zip_ref:
                zip_ref.extractall(settings.MEDIA_ROOT)
                for file_name in zip_ref.namelist():
                    clean_file_name = file_name
                    while clean_file_name.startswith('media/'):
                        clean_file_name = clean_file_name[len('media/'):]
                    media_path = os.path.join('media', clean_file_name).replace('\\', '/')
                    folder_name = os.path.dirname(clean_file_name).strip('/')
                    folder = None
                    if folder_name:
                        folder, _ = Folder.objects.get_or_create(name=folder_name)
                    if not Media.objects.filter(file=media_path).exists():
                        Media.objects.create(file=media_path, folder=folder)
                        logger.info(f"فایل {media_path} در پوشه {folder_name or 'root'} ثبت شد.")
                    else:
                        logger.info(f"فایل {media_path} قبلاً در دیتابیس وجود دارد.")
            logger.info("فایل ZIP با موفقیت بازگردانی شد.")
            self.message_user(request, 'فایل ZIP با موفقیت بازگردانی شد.')
            if os.path.exists(obj.zip_file.path):
                os.remove(obj.zip_file.path)
                logger.info(f"فایل ZIP {obj.zip_file.path} حذف شد.")
            obj.delete()
        except Exception as e:
            logger.error(f'خطا در بازگردانی فایل ZIP: {str(e)}')
            self.message_user(request, f'خطا در بازگردانی فایل ZIP: {str(e)}', level='error')



# بقیه کدهای admin.py بدون تغییر باقی می‌مانند
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
    list_display = ('id', 'order')

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
        if obj.icon and hasattr(obj.icon, 'svg_icon') and obj.icon.svg_icon:
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
        if obj.icon and obj.icon.svg_icon:
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
    
    
    
@admin.register(LegalProfileSubmissionRule)
class LegalProfileSubmissionRuleAdmin(admin.ModelAdmin):
    list_display = ['description']
    search_fields = ['description']
    
    def has_add_permission(self, request):
        # جلوگیری از افزودن نمونه جدید اگر یکی وجود داشته باشد
        if self.model.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # می‌توانید این را فعال یا غیرفعال کنید بسته به نیاز
        return True