from django.contrib import admin
from .models import ZarinpalGateway

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