# config/admin.py
import os
import zipfile
import io
import logging

from django.contrib import admin, messages
from django.utils.html import format_html
from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)

from .models import (
    Location, Page, HeaderMenu, QuickAccess, SiteConfig, Slide,
    Statistic, StatisticItem, ChooseReason, FAQ, Service, ContactInfo,
    SocialMedia, Banner, EnamadLicense, License, Advantage, FakeComment,
    Rule, ComingSoon, UserLevel, Folder, Media, MediaRestore,
)
from .forms import (
    SiteConfigAdminForm, SlideAdminForm, ChooseReasonForm, ServiceForm,
    BannerForm, LicenseForm, FakeCommentForm, ComingSoonAdminForm,
    StatisticAdminForm, MediaRestoreForm,
)

# تابع کمکی برای لیست کردن تمام فایل‌ها و فولدرها در MEDIA_ROOT
def list_all_files_and_dirs(base_path):
    folders = []
    files = []
    for root, dirs, filenames in os.walk(base_path):
        rel_root = os.path.relpath(root, base_path)
        if rel_root == '.':
            rel_root = ''
        for d in dirs:
            folders.append(os.path.join(rel_root, d))
        for f in filenames:
            files.append(os.path.join(rel_root, f))
    return folders, files

# اکشن ادمین برای نمایش تمام فایل‌ها و فولدرهای media
@admin.action(description='نمایش تمام فایل‌ها و فولدرهای media')
def show_all_media_files(modeladmin, request, queryset):
    base_path = settings.MEDIA_ROOT
    folders, files = list_all_files_and_dirs(base_path)
    message = "فولدرها:\n" + "\n".join(folders) + "\n\nفایل‌ها:\n" + "\n".join(files)
    messages.info(request, message[:3000])  # محدودیت طول پیام برای جلوگیری از خطا

# Inline برای مدل Media در FolderAdmin
class MediaInline(admin.TabularInline):
    model = Media
    extra = 1
    fields = ['file', 'admin_file']
    readonly_fields = ['admin_file']

# ثبت مدل Folder در ادمین
@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    list_filter = ['created_at']
    search_fields = ['name']
    inlines = [MediaInline]

# ثبت مدل Media در ادمین
@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'folder', 'admin_file')
    list_filter = ['folder']
    search_fields = ['file']
    list_editable = ['folder']
    autocomplete_fields = ['folder']
    actions = ['export_as_zip', show_all_media_files]

    def export_as_zip(self, request, queryset):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for media in queryset:
                if media.file and os.path.exists(media.file.path):
                    folder_name = media.folder.name if media.folder else ''
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

# ثبت مدل MediaRestore در ادمین
@admin.register(MediaRestore)
class MediaRestoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'zip_file', 'uploaded_at')
    list_filter = ['uploaded_at']
    readonly_fields = ['uploaded_at']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            with zipfile.ZipFile(obj.zip_file.path, 'r') as zip_ref:
                zip_ref.extractall(settings.MEDIA_ROOT)
                for file_name in zip_ref.namelist():
                    if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        clean_file_name = file_name
                        while clean_file_name.startswith('media/'):
                            clean_file_name = clean_file_name[len('media/'):]
                        media_path = os.path.join('media', clean_file_name)
                        folder_name = os.path.dirname(clean_file_name).strip('/')
                        folder = None
                        if folder_name:
                            folder, _ = Folder.objects.get_or_create(name=folder_name)
                        logger.info(f"ایجاد رکورد برای: {media_path}, پوشه: {folder_name}")
                        Media.objects.get_or_create(
                            file=media_path,
                            folder=folder
                        )
            logger.info("فایل ZIP با موفقیت بازگردانی شد.")
            messages.success(request, 'فایل ZIP با موفقیت بازگردانی شد.')
            os.remove(obj.zip_file.path)
            obj.delete()
        except Exception as e:
            logger.error(f'خطا در بازگردانی فایل ZIP: {str(e)}')
            messages.error(request, f'خطا در بازگردانی فایل ZIP: {str(e)}')

# سایر مدل‌ها را به صورت کامل و بهینه ثبت کنید:

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'page', 'path')
    search_fields = ('title', 'page', 'path')

@admin.register(HeaderMenu)
class HeaderMenuAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    def save_model(self, request, obj, form, change):
        if not change and HeaderMenu.objects.count() >= HeaderMenu.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {HeaderMenu.MAX_ALLOWED_INSTANCES} منوی هدر می‌توانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return HeaderMenu.objects.count() < HeaderMenu.MAX_ALLOWED_INSTANCES

@admin.register(QuickAccess)
class QuickAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    def save_model(self, request, obj, form, change):
        if not change and QuickAccess.objects.count() >= QuickAccess.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {QuickAccess.MAX_ALLOWED_INSTANCES} دسترسی سریع می‌توانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return QuickAccess.objects.count() < QuickAccess.MAX_ALLOWED_INSTANCES

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    form = SiteConfigAdminForm
    list_display = ('id', 'header_title', 'header_sub_title', 'footer_title')

    def save_model(self, request, obj, form, change):
        if not change and SiteConfig.objects.exists():
            messages.error(request, 'تنها یک کانفیگ برای سایت می‌توان ساخت')
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
            messages.error(request, 'تنها یک کانفیگ درباره ما می‌توان ساخت.')
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

    fieldsets = (
        (None, {
            'fields': (
                'question',
                'answer',
                'icon',
                'icon_preview',
                'page',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
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
    list_display = (
        'id', 'title', 'subtitle', 'value', 'link', 'show_in_footer', 'icon_preview'
    )
    search_fields = ('title', 'subtitle', 'value', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title', 'subtitle', 'value', 'link', 'icon', 'icon_preview', 'show_in_footer',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and hasattr(obj.icon, 'svg_icon') and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"

@admin.register(SocialMedia)
class SocialMediaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'type', 'type_fa', 'link', 'show_in_footer', 'icon_preview',
    )
    search_fields = ('type', 'type_fa', 'link', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'type', 'type_fa', 'link', 'icon', 'icon_preview', 'show_in_footer',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
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
            messages.error(request, 'تنها یک کد اینماد می‌توان ساخت')
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

    fieldsets = (
        (None, {
            'fields': (
                'title', 'subtitle', 'icon', 'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"

    def has_add_permission(self, request):
        if Advantage.objects.count() >= 4:
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
            messages.error(request, 'تنها یک کامینگ سون می‌توان ساخت')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not ComingSoon.objects.exists()

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'icon_preview')
    search_fields = ('title', 'icon__title_icon')
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title', 'icon', 'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and hasattr(obj.icon, 'svg_icon') and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'latitude', 'longitude')
    search_fields = ('latitude', 'longitude')

    def save_model(self, request, obj, form, change):
        if not change and Location.objects.exists():
            messages.error(request, 'تنها یک کانفیگ تماس با ما می‌توان ساخت.')
            return
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not Location.objects.exists()
