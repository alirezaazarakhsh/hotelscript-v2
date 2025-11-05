from django.db import models

# مدل برای تنظیمات کلی چت بات   
class BotSettings(models.Model):
    """
    مدل برای ذخیره تنظیمات کلی بات، مثل سیستم اینستراکشن، صدای پیش‌فرض، فونت‌ها و غیره.
    فقط یک رکورد از این مدل بساز (singleton-like).
    """
    google_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="کلید API گوگل (برای Gemini یا سرویس‌های دیگر). اگر خالی باشد، از .env استفاده می‌شود."
    )
    system_instruction = models.TextField(
        default="شما یک دستیار هوشمند و متخصص هتل برای وب‌سایت 'safarnameh24.com' هستید. ...",  # سیستم اینستراکشن پیش‌فرض رو اینجا بگذار (از کد Reactت کپی کن)
        help_text="دستورالعمل سیستم برای مدل AI (مثل Gemini)."
    )
    default_voice = models.CharField(
        max_length=50,
        choices=[('Kore', 'خانم'), ('Puck', 'آقا')],
        default='Kore',
        help_text="صدای پیش‌فرض بات (برای TTS)."
    )
    is_bot_voice_enabled = models.BooleanField(
        default=True,
        help_text="آیا پاسخ صوتی بات فعال باشد؟"
    )
    available_fonts = models.JSONField(
        default=list,
        help_text="لیست فونت‌های موجود، مثلاً [{'name': 'وزیرمتن', 'family': 'Vazirmatn'}]"
    )
    # اگر تنظیمات دیگه‌ای مثل theme یا hotel_links داری، اضافه کن
    hotel_links = models.JSONField(
        default=list,
        blank=True,
        help_text="لیست لینک‌های هتل‌ها به صورت JSON، مثلاً [{'name': 'هتل X', 'url': 'https://...'}]"
    )

    class Meta:
        verbose_name = "تنظیمات چت بات"
        verbose_name_plural = "تنظیمات چت بات"

    def __str__(self):
        return "تنظیمات کلی بات"
    
    


# مدل سوال و جواب چت بات 
class FAQ(models.Model):
    """
    مدل برای سوالات متداول (FAQ). برای پاسخ‌های ثابت مثل ساعت کاری، قیمت‌ها و غیره.
    """
    question = models.CharField(
        max_length=255,
        help_text="سوال کاربر (مثل 'ساعت کاری سایت چنده؟')"
    )
    answer = models.TextField(
        help_text="پاسخ ثابت به سوال."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="آیا این FAQ فعال باشد؟"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سوال و جواب"
        verbose_name_plural = "سوال و جواب های چت بات"
        ordering = ['-created_at']  # جدیدترین اول

    def __str__(self):
        return self.question