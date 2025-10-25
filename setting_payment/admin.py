from django.contrib import admin
from django.contrib import messages
from .models import ZarinpalGateway, IranianGateway, PaymentGatewayPreference

@admin.register(ZarinpalGateway)
class ZarinpalGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code',)
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )

    def has_add_permission(self, request):
        if ZarinpalGateway.objects.exists():
            messages.warning(request, "تنها یک تنظیم برای درگاه زرین‌پال مجاز است.")
        return not ZarinpalGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(IranianGateway)
class IranianGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code',)
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )

    def has_add_permission(self, request):
        if IranianGateway.objects.exists():
            messages.warning(request, "تنها یک تنظیم برای درگاه ایران درگاه مجاز است.")
        return not IranianGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(PaymentGatewayPreference)
class PaymentGatewayPreferenceAdmin(admin.ModelAdmin):
    list_display = ('active_gateway',)
    list_display_links = ('active_gateway',)
    fieldsets = (
        (None, {
            'fields': ('active_gateway',)
        }),
    )

    def has_add_permission(self, request):
        if PaymentGatewayPreference.objects.exists():
            messages.warning(request, "تنها یک تنظیم ترجیحات درگاه پرداخت مجاز است.")
        return not PaymentGatewayPreference.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:  # اگر شیء در حال ویرایش باشد
            return ('active_gateway',)  # فقط active_gateway رو فقط‌خواندنی می‌کنیم
        return ()