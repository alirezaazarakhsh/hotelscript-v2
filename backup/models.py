from django.db import models
from django.utils.translation import gettext_lazy as _

class AppModule(models.Model):
    name = models.CharField(
        verbose_name=_("نام اپلیکیشن"),
        max_length=100,
        unique=True,
        help_text=_("نام کوتاه اپلیکیشن (مثلا users، blog)")
    )
    verbose_name = models.CharField(
        verbose_name=_("نام نمایشی"),
        max_length=150,
        blank=True,
        null=True,
        help_text=_("نام قابل نمایش اپلیکیشن")
    )

    class Meta:
        verbose_name = _("اپلیکیشن")
        verbose_name_plural = _("اپلیکیشن‌ها")
        ordering = ['name']

    def __str__(self):
        return self.verbose_name or self.name


class AppModel(models.Model):
    """
    مدل‌های مربوط به هر اپلیکیشن
    """
    app = models.ForeignKey(
        AppModule,
        verbose_name=_("اپلیکیشن"),
        on_delete=models.CASCADE,
        related_name='models'
    )
    name = models.CharField(
        verbose_name=_("نام مدل"),
        max_length=150,
        help_text=_("نام مدل Django (مثلا Post, Comment, UserProfile)")
    )
    verbose_name = models.CharField(
        verbose_name=_("نام نمایشی مدل"),
        max_length=150,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("مدل اپلیکیشن")
        verbose_name_plural = _("مدل‌های اپلیکیشن")
        ordering = ['app', 'name']

    def __str__(self):
        return self.verbose_name or self.name


class Backup(models.Model):
    """
    مدل بکاپ‌ها
    """
    app = models.ForeignKey(
        AppModule,
        verbose_name=_("اپلیکیشن"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("اپلیکیشنی که بکاپ آن گرفته شده؛ اگر خالی باشد بکاپ کل دیتابیس است")
    )
    app_model = models.ForeignKey(
        AppModel,
        verbose_name=_("مدل اپ"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("اگر این فیلد مقدار داشته باشد، بکاپ مربوط به آن مدل است")
    )
    file = models.FileField(
        verbose_name=_("فایل بکاپ"),
        upload_to='backups/'
    )
    created_at = models.DateTimeField(
        verbose_name=_("تاریخ ایجاد"),
        auto_now_add=True
    )
    restored = models.BooleanField(
        verbose_name=_("ری‌استور شده؟"),
        default=False,
        help_text=_("آیا این بکاپ ری‌استور شده است")
    )
    is_full_backup = models.BooleanField(
        verbose_name=_("بکاپ کامل"),
        default=False,
        help_text=_("آیا بکاپ مربوط به کل دیتابیس است")
    )

    class Meta:
        verbose_name = _("بکاپ")
        verbose_name_plural = _("بکاپ‌ها")
        ordering = ['-created_at']

    def __str__(self):
        if self.is_full_backup:
            return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - بکاپ کل دیتابیس"
        elif self.app_model:
            return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - بکاپ مدل {self.app_model} از اپ {self.app}"
        elif self.app:
            return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - بکاپ اپ {self.app}"
        else:
            return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - بکاپ نامشخص"
