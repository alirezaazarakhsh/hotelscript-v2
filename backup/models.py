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

    backup_type = models.CharField(max_length=10, choices=BACKUP_TYPE_CHOICES)
    app_name = models.CharField(max_length=100, blank=True, null=True)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.backup_type.upper()} - {self.app_name or 'ALL'} - {self.model_name or 'ALL'} - {self.created_at.date()}"

    def get_backup_folder_path(self):
        """مسیر فولدر بکاپ"""
        return os.path.join(settings.BASE_DIR, 'backup', 'folder-save-backup')

    class Meta:
        verbose_name = "بکاپ گیری"
        verbose_name_plural = "بکاپ گیری"


class BackupRestoreRequest(models.Model):
    backup_file = models.FileField(upload_to='restore/')
    restore_type = models.CharField(max_length=10, choices=BackupLog.BACKUP_TYPE_CHOICES)
    app_name = models.CharField(max_length=100, blank=True, null=True)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    restored = models.BooleanField(default=False)

    def __str__(self):
        return f"Restore {self.restore_type.upper()} at {self.requested_at}"

    class Meta:
        verbose_name = "ریستور"
        verbose_name_plural = "ریستور"
