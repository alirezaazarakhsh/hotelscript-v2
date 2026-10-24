from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# درگاه پرداخت زرین‌پال
class ZarinpalGateway(models.Model):
    """
    مدل تنظیمات درگاه زرین‌پال.
    این مدل برای ذخیره مرچنت‌کد، حالت درگاه (سندباکس یا پروداکشن)، URLهای مربوط به درخواست، پرداخت و تأیید، و URL ریدایرکت استفاده می‌شود.
    **توجه**: در حالت پروداکشن، URLها باید به جای 'sandbox' از 'payment' استفاده کنند.
    مثال:
    - سندباکس: https://sandbox.zarinpal.com/pg/v4/payment/request.json
    - پروداکشن: https://payment.zarinpal.com/pg/v4/payment/request.json
    """

    MODE_CHOICES = (
        ('sandbox', 'سندباکس'),
        ('production', 'پروداکشن'),
    )

    merchant_code = models.CharField(
        max_length=36,
        unique=True,
        verbose_name="مرچند کد زرین‌پال",
        help_text="مرچند کد ارائه‌شده توسط زرین‌پال (36 کاراکتر). برای سندباکس می‌تواند تصادفی باشد، اما برای پروداکشن باید معتبر باشد."
    )
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='sandbox',
        verbose_name="حالت درگاه",
        help_text="حالت سندباکس برای تست و پروداکشن برای محیط واقعی. در حالت پروداکشن، URLها باید شامل 'payment' باشند."
    )
    request_url = models.URLField(
        default='https://sandbox.zarinpal.com/pg/v4/payment/request.json',
        verbose_name="URL درخواست پرداخت",
        validators=[URLValidator()],
        help_text="URL درخواست پرداخت زرین‌پال. برای پروداکشن از 'https://payment.zarinpal.com/pg/v4/payment/request.json' استفاده کنید."
    )
    payment_url = models.URLField(
        default='https://sandbox.zarinpal.com/pg/StartPay',
        verbose_name="URL صفحه پرداخت",
        validators=[URLValidator()],
        help_text="URL صفحه پرداخت زرین‌پال. برای پروداکشن از 'https://payment.zarinpal.com/pg/StartPay' استفاده کنید."
    )
    verify_url = models.URLField(
        default='https://sandbox.zarinpal.com/pg/v4/payment/verify.json',
        verbose_name="URL تأیید پرداخت",
        validators=[URLValidator()],
        help_text="URL تأیید پرداخت زرین‌پال. برای پروداکشن از 'https://payment.zarinpal.com/pg/v4/payment/verify.json' استفاده کنید."
    )
    callback_redirect_url = models.URLField(
        default='https://zarvantrip.com/payment/watcher-info',
        verbose_name="URL ریدایرکت callback",
        validators=[URLValidator()],
        help_text="URL پایه برای ریدایرکت پس از callback پرداخت. مثال: https://zarvantrip.com/payment/watcher-info"
    )

    def __str__(self):
        return f"زرین‌پال - {self.merchant_code} ({self.get_mode_display()})"

    def save(self, *args, **kwargs):
        # اطمینان از وجود تنها یک نمونه
        if not self.pk and ZarinpalGateway.objects.exists():
            raise ValidationError("تنها یک تنظیم درگاه زرین‌پال مجاز است.")
        # اعتبارسنجی URLها بر اساس حالت
        if self.mode == 'production':
            if 'sandbox' in self.request_url or 'sandbox' in self.payment_url or 'sandbox' in self.verify_url:
                raise ValidationError(
                    "در حالت پروداکشن، URLها نباید شامل 'sandbox' باشند. "
                    "لطفاً از URLهای پروداکشن استفاده کنید، مانند: "
                    "https://payment.zarinpal.com/pg/v4/payment/request.json"
                )
            if 'payment' not in self.request_url or 'payment' not in self.payment_url or 'payment' not in self.verify_url:
                raise ValidationError(
                    "در حالت پروداکشن، URLها باید شامل 'payment' باشند. "
                    "لطفاً از URLهای پروداکشن استفاده کنید، مانند: "
                    "https://payment.zarinpal.com/pg/v4/payment/request.json"
                )
        else:  # حالت سندباکس
            if 'sandbox' not in self.request_url or 'sandbox' not in self.payment_url or 'sandbox' not in self.verify_url:
                raise ValidationError(
                    "در حالت سندباکس، URLها باید شامل 'sandbox' باشند. "
                    "لطفاً از URLهای سندباکس استفاده کنید، مانند: "
                    "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
                )
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "تنظیمات درگاه زرین‌پال"
        verbose_name_plural = "تنظیمات درگاه زرین‌پال"

# درگاه پرداخت ایران‌درگاه
class IranianGateway(models.Model):
    """
    مدل تنظیمات درگاه ایران‌درگاه.
    این مدل برای ذخیره مرچنت‌کد، URLهای مربوط به درخواست، پرداخت و تأیید، و URL ریدایرکت استفاده می‌شود.
    **توجه**: URLهای پیش‌فرض برای ایران‌درگاه مناسب هستند، اما در صورت نیاز می‌توانید آن‌ها را تغییر دهید.
    مثال:
    - درخواست: https://dargaah.ir/payment
    - پرداخت: https://dargaah.ir/ird/startpay
    - تأیید: https://dargaah.ir/verification
    """

    merchant_code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="مرچند کد ایران‌درگاه",
        help_text="مرچند کد ارائه‌شده توسط ایران‌درگاه."
    )
    request_url = models.URLField(
        default='https://dargaah.ir/payment',
        verbose_name="URL درخواست پرداخت",
        validators=[URLValidator()],
        help_text="URL درخواست پرداخت ایران‌درگاه. معمولاً نیازی به تغییر ندارد."
    )
    payment_url = models.URLField(
        default='https://dargaah.ir/ird/startpay',
        verbose_name="URL صفحه پرداخت",
        validators=[URLValidator()],
        help_text="URL صفحه پرداخت ایران‌درگاه. معمولاً نیازی به تغییر ندارد."
    )
    verify_url = models.URLField(
        default='https://dargaah.ir/verification',
        verbose_name="URL تأیید پرداخت",
        validators=[URLValidator()],
        help_text="URL تأیید پرداخت ایران‌درگاه. معمولاً نیازی به تغییر ندارد."
    )
    callback_redirect_url = models.URLField(
        default='https://zarvantrip.com/payment/watcher-info',
        verbose_name="URL ریدایرکت callback",
        validators=[URLValidator()],
        help_text="URL پایه برای ریدایرکت پس از callback پرداخت. مثال: https://zarvantrip.com/payment/watcher-info"
    )

    def __str__(self):
        return f"ایران‌درگاه - {self.merchant_code}"

    def save(self, *args, **kwargs):
        # اطمینان از وجود تنها یک نمونه
        if not self.pk and IranianGateway.objects.exists():
            raise ValidationError("تنها یک تنظیم درگاه ایران‌درگاه مجاز است.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "تنظیمات درگاه ایران‌درگاه"
        verbose_name_plural = "تنظیمات درگاه ایران‌درگاه"

# انتخاب درگاه برای فعال بودن توسط کاربر
class PaymentGatewayPreference(models.Model):
    """
    مدل تنظیم درگاه فعال.
    این مدل مشخص می‌کند که کدام درگاه (زرین‌پال یا ایران‌درگاه) به عنوان درگاه فعال استفاده شود.
    """

    GATEWAY_CHOICES = (
        ('zarinpal', 'زرین‌پال'),
        ('iraniangateway', 'ایران‌درگاه'),
    )
    active_gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default='zarinpal',
        verbose_name="تنظیمات تغییر درگاه پرداخت",
        help_text="درگاه فعال را انتخاب کنید."
    )

    def __str__(self):
        return f"درگاه فعال: {self.get_active_gateway_display()}"

    def save(self, *args, **kwargs):
        if not self.pk and PaymentGatewayPreference.objects.exists():
            raise ValidationError("تنها یک تنظیم ترجیحات درگاه پرداخت مجاز است.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "درگاه"
        verbose_name_plural = "تنظیمات درگاه پرداخت"