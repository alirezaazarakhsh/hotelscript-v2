from django.contrib import admin
from django.contrib import messages
from .models import (
    Location,
    Page,
    HeaderMenu,
    QuickAccess,
    # Section,
    SiteConfig,
    Slide,
    Statistic,
    StatisticItem,
    ChooseReason,
    FAQ,
    Service,
    ContactInfo,
    SocialMedia,
    Banner,
    EnamadLicense,
    License,
    Advantage,
    FakeComment,
    Rule,
    ComingSoon,
    UserLevel,
)
from .forms import (
    SiteConfigAdminForm,
    SlideAdminForm,
    ChooseReasonForm,
    ServiceForm,
    BannerForm,
    LicenseForm,
    FakeCommentForm,
    ComingSoonAdminForm,
    StatisticAdminForm,
)


# ثبت مدل Page در ادمین با نمایش ستون‌های مشخص و قابلیت جستجو
@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'page', 'path')
    search_fields = ('title', 'page', 'path')


# ثبت مدل HeaderMenu در ادمین با محدودیت تعداد ایجاد منوها
@admin.register(HeaderMenu)
class HeaderMenuAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    # جلوگیری از ساخت بیش از تعداد مجاز منو
    def save_model(self, request, obj, form, change):
        if not change and HeaderMenu.objects.count() >= HeaderMenu.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {HeaderMenu.MAX_ALLOWED_INSTANCES} منوی هدر میتوانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    # اجازه افزودن منو فقط در صورت کمتر بودن تعداد موجود از حد مجاز
    def has_add_permission(self, request):
        return HeaderMenu.objects.count() < HeaderMenu.MAX_ALLOWED_INSTANCES


# ثبت مدل QuickAccess در ادمین با محدودیت تعداد دسترسی‌های سریع
@admin.register(QuickAccess)
class QuickAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'title', 'page')
    search_fields = ('order', 'title', 'page')

    # جلوگیری از ساخت بیش از تعداد مجاز دسترسی سریع
    def save_model(self, request, obj, form, change):
        if not change and QuickAccess.objects.count() >= QuickAccess.MAX_ALLOWED_INSTANCES:
            messages.error(request, f'تنها به تعداد {QuickAccess.MAX_ALLOWED_INSTANCES} دسترسی سریع میتوانید بسازید.')
        else:
            super().save_model(request, obj, form, change)

    # اجازه افزودن فقط اگر تعداد دسترسی‌های سریع کمتر از حد مجاز باشد
    def has_add_permission(self, request):
        return QuickAccess.objects.count() < QuickAccess.MAX_ALLOWED_INSTANCES



# ثبت مدل SiteConfig در ادمین با محدودیت ایجاد تنها یک نمونه
@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    form = SiteConfigAdminForm
    list_display = ('id', 'header_title', 'header_sub_title', 'footer_title')

    # جلوگیری از ساخت بیش از یک کانفیگ سایت
    def save_model(self, request, obj, form, change):
        if not change and SiteConfig.objects.exists():
            messages.error(request, 'تنها یک کانفیگ برای سایت میتوان ساخت')
        else:
            super().save_model(request, obj, form, change)

    # اجازه افزودن تنها در صورت عدم وجود کانفیگ قبلی
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()


# ثبت مدل Slide در ادمین همراه با فرم سفارشی
@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    form = SlideAdminForm
    list_display = ('id', 'order')


# تعریف Inline برای مدل StatisticItem (آیتم‌های آماری) جهت نمایش تو در تو در بخش ادمین
class StatisticItemInline(admin.TabularInline):
    model = StatisticItem
    extra = 1

    def get_max_num(self, request, obj=None, **kwargs):
        return 1

@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    form = StatisticAdminForm
    list_display = ('id', 'title', 'description')
    inlines = [StatisticItemInline]

    # جلوگیری از ثبت بیش از یک آمار
    def save_model(self, request, obj, form, change):
        if not change and Statistic.objects.exists():
            messages.error(request, 'تنها یک کانفیگ درباره ما می‌توان ساخت.')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not Statistic.objects.exists()


# ثبت مدل ChooseReason در ادمین با فرم سفارشی
@admin.register(ChooseReason)
class ChooseReasonAdmin(admin.ModelAdmin):
    form = ChooseReasonForm
    list_display = ('id', 'title', 'description')


# ثبت مدل FAQ در ادمین با قابلیت جستجو
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer')
    search_fields = ('question', 'answer')


# ثبت مدل Service در ادمین با فرم سفارشی و جستجو
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    form = ServiceForm
    list_display = ('id', 'title', 'description')
    search_fields = ('title', 'description')


# ثبت مدل ContactInfo در ادمین با جستجو
@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'value')
    search_fields = ('title', 'subtitle', 'value')


# ثبت مدل SocialMedia در ادمین با قابلیت جستجو
@admin.register(SocialMedia)
class SocialMediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'link')
    search_fields = ('type', 'link')


# ثبت مدل Banner در ادمین با فرم سفارشی، فیلتر و جستجو
@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerForm
    list_display = ('id', 'page', 'order', 'title', 'link')
    search_fields = ('title', 'link')
    list_filter = ('page',)


# ثبت مدل EnamadLicense در ادمین با محدودیت ایجاد تنها یک نمونه
@admin.register(EnamadLicense)
class EnamadLicenseAdmin(admin.ModelAdmin):
    list_display = ('id',)

    # جلوگیری از ساخت بیش از یک کد اینماد
    def save_model(self, request, obj, form, change):
        if not change and EnamadLicense.objects.exists():
            messages.error(request, 'تنها یک کد اینماد میتوان ساخت')
        else:
            super().save_model(request, obj, form, change)

    # اجازه افزودن تنها در صورت عدم وجود نمونه قبلی
    def has_add_permission(self, request):
        return not EnamadLicense.objects.exists()


# ثبت مدل License در ادمین با فرم سفارشی و جستجو
@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    form = LicenseForm
    list_display = ('id', 'link')
    search_fields = ('link',)


# ثبت مدل Advantage در ادمین با قابلیت جستجو
@admin.register(Advantage)
class AdvantageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle')
    search_fields = ('title', 'subtitle',)


# ثبت مدل FakeComment در ادمین با فرم سفارشی و جستجو
@admin.register(FakeComment)
class FakeCommentAdmin(admin.ModelAdmin):
    form = FakeCommentForm
    list_display = ('id', 'commenter', 'evaluation', 'text', 'rate')
    search_fields = ('commenter', 'text')


# ثبت مدل Rule در ادمین با قابلیت جستجو
@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'tab_title')
    search_fields = ('tab_title', 'text')


# ثبت مدل ComingSoon در ادمین با فرم سفارشی و محدودیت ایجاد تنها یک نمونه
@admin.register(ComingSoon)
class ComingSoonAdmin(admin.ModelAdmin):
    form = ComingSoonAdminForm
    list_display = ('id', 'title', 'subtitle', 'end_date', 'copyright_text', 'is_active')

    # جلوگیری از ساخت بیش از یک کامینگ سون
    def save_model(self, request, obj, form, change):
        if not change and ComingSoon.objects.exists():
            messages.error(request, 'تنها یک کامینگ سون میتوان ساخت')
        else:
            super().save_model(request, obj, form, change)

    # اجازه افزودن تنها در صورت عدم وجود نمونه قبلی
    def has_add_permission(self, request):
        return not ComingSoon.objects.exists()


# ثبت مدل UserLevel در ادمین با قابلیت جستجو
@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)


#ادمین کانفیگ تماس با ما 
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