# backup/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class AppModule(models.Model):
    """
    مدل اپلیکیشن‌های پروژه
    هر اپلیکیشنی که در پروژه وجود دارد اینجا ذخیره می‌شود.
    """
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


class Backup(models.Model):
    """
    مدل بکاپ‌ها
    اطلاعات بکاپ‌هایی که گرفته شده شامل فایل بکاپ، اپلیکیشن مرتبط، تاریخ و وضعیت ری‌استور.
    """
    app = models.ForeignKey(
        AppModule,
        verbose_name=_("اپلیکیشن"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("اپلیکیشنی که بکاپ آن گرفته شده؛ اگر خالی باشد بکاپ کل دیتابیس است")
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
        else:
            return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - بکاپ اپ {self.app}"
