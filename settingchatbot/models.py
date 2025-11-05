from django.db import models
from django.contrib.postgres.fields import JSONField # برای Django 3.1 به بعد
# اگر از نسخه‌های قدیمی‌تر Django (قبل از 3.1) استفاده می‌کنید، 
# باید یک پکیج شخص ثالث مثل 'jsonfield' را نصب کرده و آن را import کنید:
# from jsonfield import JSONField 

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
        default="شما یک دستیار هوشمند و متخصص هتل برای وب‌سایت 'safarnameh24.com' هستید. هدف اصلی شما کمک به کاربران در پیدا کردن و رزرو هتل از طریق پرسیدن سوالات مرتبط، ارائه اطلاعات دقیق در مورد هتل‌ها و راهنمایی برای استفاده از امکانات وب‌سایت است. لطفا در پاسخ‌های خود بسیار دوستانه، مفید و دقیق باشید و در صورت نیاز، کاربران را به صفحات مرتبط در وب‌سایت (اگر در سوالات متداول یا لینک‌ها موجود باشد) ارجاع دهید. همیشه سعی کنید راه حل‌های کاربردی و اطلاعات کامل ارائه دهید تا کاربر بهترین تجربه را داشته باشد. به هیچ عنوان اطلاعات نامربوط به هتل و وب‌سایت safarnameh24.com ارائه ندهید. زبان شما فارسی است. شما می‌توانید پاسخ‌های خود را به صورت صوتی نیز ارائه دهید. اگر کاربر درخواست پاسخ صوتی کرد، از قابلیت TTS استفاده کنید.",
        help_text="دستورالعمل سیستم برای مدل AI (مثل Gemini)."
    )
    
    # انتخاب‌های صدای حرفه‌ای‌تر برای Google Cloud Text-to-Speech API
    # شما باید این نام‌ها را از مستندات رسمی Google Cloud Text-to-Speech پیدا کنید.
    # این لیست شامل نام‌های رایج برای فارسی و همچنین گزینه‌های Gemini شماست.
    # در نهایت، نام‌هایی را که واقعاً توسط API شما پشتیبانی می‌شوند، نگه‌دارید.
    VOICE_CHOICES = [
        # Google Cloud Text-to-Speech Standard Voices for Farsi (مثال)
        ('fa-IR-Standard-A', 'فارسی - صدای استاندارد زنانه (A)'),
        ('fa-IR-Standard-B', 'فارسی - صدای استاندارد مردانه (B)'),
        # Google Cloud Text-to-Speech WaveNet Voices for Farsi (مثال) - کیفیت بالاتر
        ('fa-IR-Wavenet-C', 'فارسی - صدای WaveNet زنانه (C)'),
        ('fa-IR-Wavenet-D', 'فارسی - صدای WaveNet مردانه (D)'),
        # اگر Gemini نام‌های خاص خودش را برای صداهای پیش‌ساخته دارد، می‌توانید آن‌ها را هم اینجا اضافه کنید
        ('Kore', 'Kore (پیش‌فرض Gemini، زنانه)'), 
        ('Puck', 'Puck (پیش‌فرض Gemini، مردانه)'),
    ]

    default_voice = models.CharField(
        max_length=50,
        choices=VOICE_CHOICES,
        default='fa-IR-Wavenet-C', # پیش‌فرض به یک صدای WaveNet با کیفیت بالاتر
        help_text="صدای پیش‌فرض بات (برای TTS). WaveNet کیفیت بالاتری دارد و توصیه می‌شود."
    )
    is_bot_voice_enabled = models.BooleanField(
        default=True,
        help_text="آیا پاسخ صوتی بات فعال باشد؟"
    )
    
    # اضافه شدن فیلد برای لینک‌های هتل
    # JSONField برای ذخیره لیستی از دیکشنری‌ها (مثل {name: "نام", url: "لینک"}) مناسب است.
    # برای Django 3.1 به بالا از django.db.models.JSONField استفاده کنید.
    # برای نسخه‌های قدیمی‌تر، یک پکیج مانند 'jsonfield' را نصب کنید.
    # در اینجا از django.db.models.JSONField استفاده شده است. اگر خطایی گرفتید، 
    # ممکن است نیاز به تغییر به django.contrib.postgres.fields.JSONField
    # یا استفاده از پکیج jsonfield داشته باشید.
    hotel_links = models.JSONField(
        default=list, # پیش‌فرض یک لیست خالی است
        blank=True,
        help_text="لیستی از لینک‌های هتل به صورت JSON (مثال: [{'name': 'هتل اسپیناس', 'url': 'https://...'}])."
    )

    # اضافه کردن فیلد برای لوگو
    logo = models.ImageField(
        upload_to='logos/',
        null=True,
        blank=True,
        help_text="لوگوی چت‌بات (برای نمایش در فرانت‌اند)."
    )

    # اضافه کردن فیلد برای عنوان خوش‌آمدگویی
    welcome_title = models.CharField(
        max_length=255,
        default="چت بات هوشمند سفرنامه ۲۴",
        help_text="عنوان خوش‌آمدگویی در صفحه اصلی چت‌بات."
    )

    # اضافه کردن فیلد برای پیام خوش‌آمدگویی
    welcome_message = models.TextField(
        default="به چت بات هوشمند سفرنامه ۲۴ خوش آمدید. اگر نیاز به مشاوره قبل از خرید یا انتخاب دارید، این چت بات نیاز شما را برطرف می‌کند. لطفا safarnameh24.com را دنبال کنید.",
        help_text="پیام خوش‌آمدگویی کامل در صفحه اصلی چت‌بات."
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
        ordering = ['question'] # مثلاً بر اساس سوال به ترتیب الفبا

    def __str__(self):
        return self.question