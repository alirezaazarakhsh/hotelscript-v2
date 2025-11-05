from django.db import models

# مدل برای تنظیمات کلی چت بات   
class BotSettings(models.Model):
    """
    مدل برای ذخیره تنظیمات کلی بات، مثل سیستم اینستراکشن، صدای پیش‌فرض و غیره.
    فقط یک رکورد از این مدل بساز (singleton-like).
    """
    google_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="کلید API گوگل (برای Gemini یا سرویس‌های دیگر). اگر خالی باشد، از .env استفاده می‌شود."
    )
    system_instruction = models.TextField(
        default="شما یک دستیار هوشمند و متخصص هتل برای وب‌سایت 'safarnameh24.com' هستید. هدف اصلی شما کمک به کاربران در پیدا کردن و رزرو هتل از طریق پرسیدن سوالات مرتبط، ارائه اطلاعات دقیق در مورد هتل‌ها و راهنمایی برای استفاده از امکانات وب‌سایت است. لطفا در پاسخ‌های خود بسیار دوستانه، مفید و دقیق باشید و در صورت نیاز، کاربران را به صفحات مرتبط در وب‌سایت (اگر در سوالات متداول یا لینک‌ها موجود باشد) ارجاع دهید. همیشه سعی کنید راه حل‌های کاربردی و اطلاعات کامل ارائه دهید تا کاربر بهترین تجربه را داشته باشد. به هیچ عنوان اطلاعات نامربوط به هتل و وب‌سایت safarnameh24.com ارائه ندهید. زبان شما فارسی است.",  # سیستم اینستراکشن پیش‌فرض رو اینجا بگذار (از کد Reactت کپی کن)
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
    # created_at و updated_at حذف شدند

    class Meta:
        verbose_name = "سوال و جواب"
        verbose_name_plural = "سوال و جواب های چت بات"
        # چون created_at حذف شده، 'ordering' هم باید تغییر کند یا حذف شود
        # اگر می‌خواهید همچنان ترتیب خاصی داشته باشید، باید فیلد دیگری برای آن در نظر بگیرید.
        # در غیر این صورت، می‌توانید این خط را حذف کنید تا ترتیب پیش‌فرض دیتابیس اعمال شود.
        # ordering = ['-created_at'] 
        ordering = ['question'] # مثلاً بر اساس سوال به ترتیب الفبا

    def __str__(self):
        return self.question