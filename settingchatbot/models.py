from django.db import models
from django.contrib.postgres.fields import JSONField  # برای Django 3.1 به بعد

class BotSettings(models.Model):
    google_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="کلید API گوگل (برای Gemini یا سرویس‌های دیگر). اگر خالی باشد، از .env استفاده می‌شود."
    )
    system_instruction = models.TextField(
        default="شما یک دستیار هوشمند و متخصص هتل برای وب‌سایت 'zarvantrip.com' هستید. هدف اصلی شما کمک به کاربران در پیدا کردن و رزرو هتل از طریق پرسیدن سوالات مرتبط، ارائه اطلاعات دقیق در مورد هتل‌ها و راهنمایی برای استفاده از امکانات وب‌سایت است. لطفا در پاسخ‌های خود بسیار دوستانه، مفید و دقیق باشید و در صورت نیاز، کاربران را به صفحات مرتبط در وب‌سایت (اگر در سوالات متداول یا لینک‌ها موجود باشد) ارجاع دهید. همیشه سعی کنید راه حل‌های کاربردی و اطلاعات کامل ارائه دهید تا کاربر بهترین تجربه را داشته باشد. به هیچ عنوان اطلاعات نامربوط به هتل و وب‌سایت zarvantrip.com ارائه ندهید. زبان شما فارسی است. شما می‌توانید پاسخ‌های خود را به صورت صوتی نیز ارائه دهید. اگر کاربر درخواست پاسخ صوتی کرد، از قابلیت TTS استفاده کنید.",
        help_text="دستورالعمل سیستم برای مدل AI (مثل Gemini)."
    )
    
    VOICE_CHOICES = [
        ('fa-IR-Standard-A', 'فارسی - صدای استاندارد زنانه (A)'),
        ('fa-IR-Standard-B', 'فارسی - صدای استاندارد مردانه (B)'),
        ('fa-IR-Wavenet-C', 'فارسی - صدای WaveNet زنانه (C)'),
        ('fa-IR-Wavenet-D', 'فارسی - صدای WaveNet مردانه (D)'),
        ('Kore', 'Kore (پیش‌فرض Gemini، زنانه)'), 
        ('Puck', 'Puck (پیش‌فرض Gemini، مردانه)'),
    ]

    default_voice = models.CharField(
        max_length=50,
        choices=VOICE_CHOICES,
        default='fa-IR-Wavenet-C',
        help_text="صدای پیش‌فرض بات (برای TTS). WaveNet کیفیت بالاتری دارد و توصیه می‌شود."
    )
    is_bot_voice_enabled = models.BooleanField(
        default=True,
        help_text="آیا پاسخ صوتی بات فعال باشد؟"
    )

    logo = models.ImageField(
        upload_to='logos/',
        null=True,
        blank=True,
        help_text="لوگوی چت‌بات (برای نمایش در فرانت‌اند)."
    )

    welcome_title = models.CharField(
        max_length=255,
        default="چت بات هوشمند سفرنامه ۲۴",
        help_text="عنوان خوش‌آمدگویی در صفحه اصلی چت‌بات."
    )

    welcome_message = models.TextField(
        default="به چت بات هوشمند سفرنامه ۲۴ خوش آمدید. اگر نیاز به مشاوره قبل از خرید یا انتخاب دارید، این چت بات نیاز شما را برطرف می‌کند. لطفا zarvantrip.com را دنبال کنید.",
        help_text="پیام خوش‌آمدگویی کامل در صفحه اصلی چت‌بات."
    )

    class Meta:
        verbose_name = "تنظیمات چت بات"
        verbose_name_plural = "تنظیمات چت بات"

    def __str__(self):
        return "تنظیمات کلی بات"
    
    
class FAQ(models.Model):
    question = models.CharField(
        max_length=255,
        help_text="سوال کاربر (مثال: 'ساعت کاری سایت چنده؟')"
    )
    answer = models.TextField(
        help_text="پاسخ ثابت به سوال."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="آیا این FAQ فعال باشد؟"
    )

    class Meta:
        verbose_name = "سوال و جواب"
        verbose_name_plural = "سوال و جواب های چت بات"
        ordering = ['question']

    def __str__(self):
        return self.question