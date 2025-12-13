from django.contrib import admin
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils import timezone
from django.utils.html import format_html
from .models import SubscriptionDescription, SubscriptionPackage, SubscriptionOption, SubscriptionPaymentRequest, SubscriptionPeriod

class SubscriptionOptionInline(admin.TabularInline):
    model = SubscriptionOption
    extra = 4  # تعداد فرم‌های خالی برای اضافه کردن
    max_num = 4  # حداکثر ۴ آپشن

@admin.register(SubscriptionPeriod)
class SubscriptionPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name')
    search_fields = ('name', 'display_name')

@admin.register(SubscriptionDescription)
class SubscriptionDescriptionAdmin(admin.ModelAdmin):
    list_display = ('description',)
    search_fields = ('description',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # اگر رکورد وجود داره، مستقیم به ویرایش برو
        queryset = self.get_queryset(request)
        if queryset.exists():
            obj = queryset.first()  # فرض می‌کنیم همیشه یکی هست
            return redirect('admin:user_subscription_settings_subscriptiondescription_change', obj.pk)
        else:
            # اگر هیچ رکورد نباشه، یکی بسازه و برو به ویرایش
            obj = SubscriptionDescription.objects.create(description='')
            return redirect('admin:user_subscription_settings_subscriptiondescription_change', obj.pk)

@admin.register(SubscriptionPackage)
class SubscriptionPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_cost', 'color', 'upgrade_to_level', 'period_fk')
    search_fields = ('name',)
    inlines = [SubscriptionOptionInline]
    autocomplete_fields = ['upgrade_to_level', 'period_fk']

@admin.register(SubscriptionPaymentRequest)
class SubscriptionPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'package', 'full_name', 'phone_number', 'approved', 'receipt_image')
    list_filter = ('approved',)
    search_fields = ('user__username', 'full_name', 'phone_number')
    readonly_fields = ('receipt_preview',)
    autocomplete_fields = ('user', 'package')

    def receipt_image(self, obj):
        if obj.receipt:
            return format_html('<img src="{}" width="50" height="50" />', obj.receipt.url)
        return "بدون تصویر"
    receipt_image.short_description = "فیش واریزی"

    def receipt_preview(self, obj):
        if obj.receipt:
            return format_html('<img src="{}" width="200" />', obj.receipt.url)
        return "بدون تصویر"
    receipt_preview.short_description = "پیش‌نمایش فیش واریزی"

    def save_model(self, request, obj, form, change):
        from datetime import timedelta
        from django.utils import timezone
        if change and obj.approved:
            profile = obj.user.natural_profile
            if profile:
                if obj.is_renewal:
                    # تمدید اشتراک فعلی
                    if profile.expiration_date:
                        if obj.package.period == 'monthly':
                            profile.expiration_date = (profile.expiration_date + timedelta(days=30))
                        elif obj.package.period == 'yearly':
                            profile.expiration_date = (profile.expiration_date + timedelta(days=365))
                        # اگر period نامشخص، تمدید نکن
                    if not profile.subscription_package:
                        profile.subscription_package = obj.package
                    profile.save()
                elif obj.package.upgrade_to_level:
                    # ارتقای سطح کاربری با تاریخ انقضا
                    profile.previous_level = profile.level
                    profile.level = obj.package.upgrade_to_level
                    profile.subscription_package = obj.package
                    # تنظیم تاریخ انقضا بر اساس period
                    if obj.package.period == 'monthly':
                        profile.expiration_date = (timezone.now() + timedelta(days=30)).date()
                    elif obj.package.period == 'yearly':
                        profile.expiration_date = (timezone.now() + timedelta(days=365)).date()
                    else:
                        profile.expiration_date = None  # اگر period نامشخص، دائمی نکن
                    # غیرفعال کردن تمدید خودکار پس از خرید دستی
                    profile.auto_renewal_enabled = False
                    # تنظیم هدف پیشرفت برای سطح نقره‌ای
                    if profile.level.title == 'نقره‌ای':
                        profile.progress_target = 500000000  # 500 میلیون
                        profile.progress_deadline = profile.expiration_date
                    profile.save()
        super().save_model(request, obj, form, change)
