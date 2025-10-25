from django.contrib import admin
from .models import ZarinpalGateway, IranianGateway, PaymentGatewayPreference

@admin.register(ZarinpalGateway)
class ZarinpalGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )

    def has_add_permission(self, request):
        # اگر حتی یک نمونه از ZarinpalGateway وجود داشته باشد، امکان افزودن غیرفعال می‌شود
        return not ZarinpalGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # می‌توانید حذف را غیرفعال کنید یا اجازه دهید
        return True

@admin.register(IranianGateway)
class IranianGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code',)
        }),
    )

    def has_add_permission(self, request):
        # اگر حتی یک نمونه از IranianGateway وجود داشته باشد، امکان افزودن غیرفعال می‌شود
        return not IranianGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # می‌توانید حذف را غیرفعال کنید یا اجازه دهید
        return True

@admin.register(PaymentGatewayPreference)
class PaymentGatewayPreferenceAdmin(admin.ModelAdmin):
    list_display = ('active_gateway',)
    fieldsets = (
        (None, {
            'fields': ('active_gateway',)
        }),
    )

    def has_add_permission(self, request):
        # فقط یک نمونه از PaymentGatewayPreference مجاز است
        return not PaymentGatewayPreference.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # حذف غیرفعال است تا تنظیمات سیستمی حفظ شود
        return False