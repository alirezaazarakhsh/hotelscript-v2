from django.db import models

# Choices برای بخش‌هایی که پترن دارند
PATTERN_SECTIONS = [
    ('otp', 'ارسال کد تایید (OTP) به کاربران'),
    ('welcome', 'خوش‌آمدگویی به کاربران پس از لاگین'),
    ('logout', 'خروج کاربر از حساب کاربری'),
    ('roomavailability', 'موجودی اتاق برای ادمین'),
    ('walletincrease', 'افزایش کیف پول کاربر'),
    ('discountcode', 'ارسال کد تخفیف به کاربران'),  
]

# مدل تنظیمات سامانه پیامکی کاوه نگار 
class KavenegarSMSSetting(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام سامانه")
    api_token = models.TextField(max_length=500, verbose_name="API Token")

    class Meta:
        verbose_name = "تنظیمات سامانه پیامکی کاوه‌ نگار"
        verbose_name_plural = "تنظیمات سامانه پیامکی کاوه‌ نگار"

    def __str__(self):
        return self.name

# پترن‌های پنل پیامکی کاوه نگار
class SMSPattern(models.Model):
    sms_setting = models.ForeignKey(
        KavenegarSMSSetting,
        on_delete=models.CASCADE,
        related_name='patterns',
        verbose_name="سامانه مربوطه"
    )
    name_fa = models.CharField(
        max_length=100,
        choices=PATTERN_SECTIONS,
        verbose_name="بخش مربوطه (نام فارسی پترن)",
        help_text="انتخاب کنید این پترن برای کدام بخش از سامانه استفاده می‌شود."
    )
    pattern_code = models.CharField(
        max_length=100,
        verbose_name="کد پترن (نام انگلیسی)",
        help_text="می‌توانید وارد سامانه کاوه نگار شده و در قسمت اعتبارسنجی، پترن خود را ایجاد کرده و سپس کد آن را اینجا وارد کنید."
    )

    class Meta:
        verbose_name = "پترن پیامک"
        verbose_name_plural = "پترن‌های پیامک"
        unique_together = ('sms_setting', 'name_fa')  # جلوگیری از تکرار پترن برای یک بخش

    def __str__(self):
        return f"{self.get_name_fa_display()} - {self.pattern_code}"