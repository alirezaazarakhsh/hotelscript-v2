from django.contrib import admin
from .models import ZarinpalGateway, IranianGateway, PaymentGatewayPreference


@admin.register(ZarinpalGateway)
class ZarinpalGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code', 'mode', 'request_url', 'payment_url', 'verify_url')
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code', 'mode', 'request_url', 'payment_url', 'verify_url'),
            'description': (
                '<p style="color: red; font-weight: bold;">'
                'توجه: در حالت پروداکشن، URLها باید به جای "sandbox" از "payment" استفاده کنند. '
                'مثال برای پروداکشن:<br>'
                '- URL درخواست: https://payment.zarinpal.com/pg/v4/payment/request.json<br>'
                '- URL پرداخت: https://payment.zarinpal.com/pg/StartPay<br>'
                '- URL تأیید: https://payment.zarinpal.com/pg/v4/payment/verify.json<br>'
                'در حالت سندباکس، URLها باید شامل "sandbox" باشند.'
                '</p>'
            )
        }),
    )

    def has_add_permission(self, request):
        # فقط اجازه افزودن یک نمونه
        return not ZarinpalGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # اجازه حذف برای انعطاف‌پذیری
        return True

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # سفارشی‌سازی صفحه ویرایش
        extra_context = extra_context or {}
        extra_context['title'] = "ویرایش تنظیمات درگاه زرین‌پال"
        extra_context['help_text'] = (
            "لطفاً مرچند کد معتبر و URLهای مناسب را وارد کنید. "
            "برای پروداکشن از 'payment' و برای سندباکس از 'sandbox' در URLها استفاده کنید."
        )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(IranianGateway)
class IranianGatewayAdmin(admin.ModelAdmin):
    list_display = ('merchant_code', 'request_url', 'payment_url', 'verify_url')
    list_display_links = ('merchant_code',)
    search_fields = ('merchant_code',)
    fieldsets = (
        (None, {
            'fields': ('merchant_code', 'request_url', 'payment_url', 'verify_url'),
            'description': (
                '<p style="color: blue; font-weight: bold;">'
                'توجه: URLهای پیش‌فرض ایران‌درگاه معمولاً نیازی به تغییر ندارند. '
                'در صورت نیاز به تغییر، اطمینان حاصل کنید که URLها معتبر و مطابق با مستندات ایران‌درگاه باشند. '
                'مثال:<br>'
                '- URL درخواست: https://dargaah.ir/payment<br>'
                '- URL پرداخت: https://dargaah.ir/ird/startpay<br>'
                '- URL تأیید: https://dargaah.ir/verification'
                '</p>'
            )
        }),
    )

    def has_add_permission(self, request):
        # فقط اجازه افزودن یک نمونه
        return not IranianGateway.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # اجازه حذف برای انعطاف‌پذیری
        return True

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # سفارشی‌سازی صفحه ویرایش
        extra_context = extra_context or {}
        extra_context['title'] = "ویرایش تنظیمات درگاه ایران‌درگاه"
        extra_context['help_text'] = (
            "لطفاً مرچند کد معتبر و URLهای مناسب را وارد کنید. "
            "URLهای پیش‌فرض معمولاً نیازی به تغییر ندارند."
        )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(PaymentGatewayPreference)
class PaymentGatewayPreferenceAdmin(admin.ModelAdmin):
    list_display = ('active_gateway',)
    list_display_links = ('active_gateway',)
    fieldsets = (
        (None, {
            'fields': ('active_gateway',),
            'description': (
                '<p style="color: green; font-weight: bold;">'
                'توجه: برای استفاده از درگاه زرین‌پال در حالت پروداکشن، اطمینان حاصل کنید که در تنظیمات '
                'ZarinpalGateway، URLها به جای "sandbox" از "payment" استفاده کنند. '
                'مثال: https://payment.zarinpal.com/pg/v4/payment/request.json'
                '</p>'
            )
        }),
    )

    def has_add_permission(self, request):
        # فقط اجازه افزودن یک نمونه
        return not PaymentGatewayPreference.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # جلوگیری از حذف برای حفظ تنظیمات
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # سفارشی‌سازی صفحه ویرایش
        extra_context = extra_context or {}
        extra_context['title'] = "ویرایش ترجیحات درگاه پرداخت"
        extra_context['help_text'] = (
            "برای تغییر درگاه فعال، گزینه موردنظر را انتخاب کنید. "
            "برای زرین‌پال در پروداکشن، اطمینان حاصل کنید که URLها شامل 'payment' باشند."
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        # هیچ فیلدی فقط‌خواندنی نیست
        return ()