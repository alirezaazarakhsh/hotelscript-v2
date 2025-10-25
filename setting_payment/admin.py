from django.contrib import admin
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
        # فقط اجازه افزودن یک نمونه
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
        # فقط اجازه افزودن یک نمونه
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
        # فقط اجازه افزودن یک نمونه
        return not PaymentGatewayPreference.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        # فقط وقتی نمونه‌ای وجود نداره، readonly اعمال نشه
        if not obj and not PaymentGatewayPreference.objects.exists():
            return ()
        return ()  # بعد از افزودن، هیچ فیلدی فقط‌خواندنی نمی‌شه

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # سفارشی‌سازی صفحه ویرایش برای نمایش پیام راهنما
        extra_context = extra_context or {}
        extra_context['title'] = "ویرایش ترجیحات درگاه پرداخت"
        extra_context['help_text'] = "برای تغییر درگاه فعال، گزینه موردنظر را انتخاب کنید."
        return super().change_view(request, object_id, form_url, extra_context=extra_context)