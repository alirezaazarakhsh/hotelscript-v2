import os
from django.conf import settings
from django.db import models
from django.utils import timezone

class BackupLog(models.Model):
    BACKUP_TYPE_CHOICES = [
        ('full', 'بکاپ از کل پروژه'),
        ('app', 'بکاپ از اپلیکیشن خاص'),
        ('model', 'بکاپ از مدل اپلیکیشن'),
    ]

    backup_type = models.CharField(
        max_length=10,
        choices=BACKUP_TYPE_CHOICES,
        verbose_name='تایپ بکاپ گیری'
    )
    app_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='نام اپلیکیشن')
    model_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='نام مدل')
    backup_file = models.FileField(
        upload_to='backup/folder-save-backup/',
        verbose_name='فایل بکاپ'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='زمان ایجاد')

    def __str__(self):
        return f"{self.backup_type.upper()} - {self.app_name or 'ALL'} - {self.model_name or 'ALL'} - {self.created_at.date()}"

    def get_backup_folder_path(self):
        return os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')

    class Meta:
        verbose_name = "بکاپ گیری"
        verbose_name_plural = "بکاپ گیری"


class BackupRestoreRequest(models.Model):
    backup_log = models.ForeignKey(
        BackupLog,
        on_delete=models.CASCADE,
        verbose_name="انتخاب بکاپ برای ریستور"
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان درخواست')
    restored = models.BooleanField(default=False, verbose_name='وضعیت ریستور')

    def __str__(self):
        return f"Restore {self.backup_log.backup_type.upper()} at {self.requested_at}"

    class Meta:
        verbose_name = "ریستور"
        verbose_name_plural = "ریستور"
