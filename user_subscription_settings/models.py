from django.db import models
from colorfield.fields import ColorField
from config.models import UserLevel
from django.contrib.auth import get_user_model

User = get_user_model()

class SubscriptionDescription(models.Model):
    description = models.TextField(verbose_name="توضیحات تکمیلی اشتراک")

    class Meta:
        verbose_name = "توضیحات تکمیلی اشتراک"
        verbose_name_plural = "توضیحات تکمیلی اشتراک‌ها"


class SubscriptionPeriod(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="نام دوره")
    display_name = models.CharField(max_length=50, verbose_name="نام نمایشی")

    class Meta:
        verbose_name = "دوره پرداخت"
        verbose_name_plural = "دوره‌های پرداخت"

    def __str__(self):
        return self.display_name


class SubscriptionPackage(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام پلن")
    short_description = models.CharField(max_length=255, verbose_name="توضیحات کوتاه")
    monthly_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="هزینه ماهانه")
    color = ColorField(default='#FF0000', verbose_name="رنگ")
    upgrade_to_level = models.ForeignKey(UserLevel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ارتقا به سطح کاربری")
    period_fk = models.ForeignKey(SubscriptionPeriod, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دوره پرداخت")

    @property
    def period(self):
        return self.period_fk.name if self.period_fk else None

    class Meta:
        verbose_name = "پکیج اشتراک"
        verbose_name_plural = "پکیج‌های اشتراک"

    def __str__(self):
        return self.name


class SubscriptionOption(models.Model):
    package = models.ForeignKey(SubscriptionPackage, on_delete=models.CASCADE, related_name='options', verbose_name="پکیج")
    name = models.CharField(max_length=100, verbose_name="نام آپشن")

    class Meta:
        verbose_name = "آپشن اشتراک"
        verbose_name_plural = "آپشن‌های اشتراک"

    def __str__(self):
        return self.name


class SubscriptionPaymentRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="کاربر")
    package = models.ForeignKey(SubscriptionPackage, on_delete=models.CASCADE, verbose_name="پکیج اشتراک")
    full_name = models.CharField(max_length=200, verbose_name="نام و نام خانوادگی")
    phone_number = models.CharField(max_length=15, verbose_name="شماره همراه")
    national_id = models.CharField(max_length=10, verbose_name="کد ملی")
    receipt = models.ImageField(upload_to='subscription_receipts/', verbose_name="فیش واریزی")
    approved = models.BooleanField(default=False, verbose_name="تایید شده")
    is_renewal = models.BooleanField(default=False, verbose_name="درخواست تمدید")

    class Meta:
        verbose_name = "درخواست پرداخت اشتراک"
        verbose_name_plural = "پرداخت کاربران برای ارتقا اشتراک"

    def __str__(self):
        return f"{self.user} - {self.package} - {'تایید شده' if self.approved else 'در انتظار'}"


