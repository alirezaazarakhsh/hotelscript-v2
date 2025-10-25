from django.contrib import admin
from django.contrib import messages
from .models import ZarinpalGateway, IranianGateway, PaymentGatewayPreference
from django.utils import timezone

@admin.register(ZarinpalGateway)
class ZarinpalGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code', 'created_at')
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        if ZarinpalGateway.objects.exists():
            messages.warning(request, "تنها یک تنظیم برای درگاه زرین‌پال مجاز است.")
        return not ZarinpalGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return True

    def save_model(self, request, obj, form, change):
        obj.created_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(IranianGateway)
class IranianGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code', 'created_at')
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        if IranianGateway.objects.exists():
            messages.warning(request, "تنها یک تنظیم برای درگاه ایران درگاه مجاز است.")
        return not IranianGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return True

    def save_model(self, request, obj, form, change):
        obj.created_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(PaymentGatewayPreference)
class PaymentGatewayPreferenceAdmin(admin.ModelAdmin):
    list_display = ('active_gateway', 'last_updated')
    list_display_links = ('active_gateway',)
    fieldsets = (
        (None, {
            'fields': ('active_gateway',)
        }),
    )
    readonly_fields = ('last_updated',)

    def has_add_permission(self, request):
        # فقط یک نمونه از PaymentGatewayPreference مجاز است
        if PaymentGatewayPreference.objects.exists():
            messages.warning(request, "تنها یک تنظیم ترجیحات درگاه پرداخت مجاز است.")
        return not PaymentGatewayPreference.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # حذف غیرفعال است تا تنظیمات سیستمی حفظ شود
        return False

    def save_model(self, request, obj, form, change):
        obj.last_updated = timezone.now()
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # اگر شیء در حال ویرایش باشد
            return self.readonly_fields + ('active_gateway',)
        return self.readonly_fields