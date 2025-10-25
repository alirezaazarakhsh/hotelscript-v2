from django.db import models

# درگاه پرداخت زرین پال
class ZarinpalGateway(models.Model):
    merchant_code = models.TextField(unique=True, verbose_name="مرچند کد زرین پال")

    def __str__(self):
        return f"زرین‌پال - {self.merchant_code}"

    class Meta:
        verbose_name = "تنظیمات درگاه زرین‌پال"
        verbose_name_plural = "تنظیمات درگاه‌ زرین‌پال"



# درگاه پرداخت ایران درگاه
class IranianGateway(models.Model):
    merchant_code = models.TextField(unique=True, verbose_name="مرچند کد ایران درگاه")

    def __str__(self):
        return f"ایران درگاه - {self.merchant_code}"

    class Meta:
        verbose_name = "تنظیمات درگاه ایران درگاه"
        verbose_name_plural = "تنظیمات درگاه‌ ایران درگاه"




# انتخاب درگاه برای فعال بودن توسط کاربر
class PaymentGatewayPreference(models.Model):
    GATEWAY_CHOICES = (
        ('zarinpal', 'زرین‌پال'),
        ('iraniangateway', 'ایران درگاه'),
    )
    active_gateway = models.CharField(
        max_length=20,
        choices=GATEWAY_CHOICES,
        default='zarinpal',
        verbose_name="تنظیمات تغییر درگاه پرداخت"
    )

    def __str__(self):
        return f"درگاه فعال: {self.get_active_gateway_display()}"

    class Meta:
        verbose_name = "درگاه"
        verbose_name_plural = "تنظیمات درگاه پرداخت"

    def save(self, *args, **kwargs):
        if not self.pk and PaymentGatewayPreference.objects.exists():
            raise ValueError("تنها یک تنظیم ترجیحات درگاه پرداخت مجاز است.")
        super().save(*args, **kwargs)