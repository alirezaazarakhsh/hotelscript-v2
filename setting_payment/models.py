from django.db import models

class ZarinpalGateway(models.Model):
    merchant_code = models.TextField(unique=True, verbose_name="مرچند کد زرین پال")
    def __str__(self):
        return f"زرین‌پال - {self.merchant_code}"

    class Meta:
        verbose_name = "تنظیمات درگاه زرین‌پال"
        verbose_name_plural = "تنظیمات درگاه‌ زرین‌پال"