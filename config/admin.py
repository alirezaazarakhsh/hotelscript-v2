from django.contrib import admin
from django.contrib import messages
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
    SiteConfig,
    Slide,
    Statistic,
    ChooseReason,
    FAQ,
    Service,
    ContactInfo,
    SocialMedia,
    Banner,
    EnamadLicense,
)
from .forms import (
    SiteConfigAdminForm,
    SlideAdminForm,
    ChooseReasonForm,
    BannerForm,
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

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    form = SlideAdminForm
    list_display = (
        'id',
        'order',
        'title',
        'link',
        'is_active',
    )

@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'subtitle',
    )

@admin.register(ChooseReason)
class ChooseReasonAdmin(admin.ModelAdmin):
    form = ChooseReasonForm
    list_display = (
        'id',
        'title',
        'description',
    )

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'question',
        'answer',
    )
    search_fields = (
        'question',
        'answer',
    )

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'description',
    )
    search_fields = (
        'title',
        'description',
    )

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'subtitle',
        'value',
    )
    search_fields = (
        'title',
        'subtitle',
        'value',
    )

@admin.register(SocialMedia)
class SocialMediaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'type',
        'link',
    )
    search_fields = (
        'type',
        'link',
    )

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerForm
    list_display = (
        'id',
        'page',
        'order',
        'title',
        'link',
    )
    search_fields = (
        'title',
        'link',
    )
    list_filter = (
        'page',
    )

@admin.register(EnamadLicense)
class EnamadLicenseAdmin(admin.ModelAdmin):
    list_display = (
        'id',
    )
    
    def save_model(self, request, obj, form, change):
        if not change and EnamadLicense.objects.exists():
            messages.error(request, 'تنها یک کد اینماد میتوان ساخت')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not EnamadLicense.objects.exists()
