# models.py در اپلیکیشن backup
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

class BackupLog(models.Model):
    BACKUP_TYPE_CHOICES = [
        ('full', 'Full Project'),
        ('app', 'App Only'),
        ('model', 'Single Model'),
    ]

    backup_type = models.CharField(max_length=10, choices=BACKUP_TYPE_CHOICES)
    app_name = models.CharField(max_length=100, blank=True, null=True)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    file_path = models.FilePathField(path='/path/to/backups', recursive=True, allow_files=True, allow_folders=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.backup_type.upper()} - {self.app_name or 'ALL'} - {self.model_name or 'ALL'} - {self.created_at.date()}"


class BackupRestoreRequest(models.Model):
    backup_file = models.FileField(upload_to='restore/')
    restore_type = models.CharField(max_length=10, choices=BackupLog.BACKUP_TYPE_CHOICES)
    app_name = models.CharField(max_length=100, blank=True, null=True)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    restored = models.BooleanField(default=False)

    def __str__(self):
        return f"Restore {self.restore_type.upper()} at {self.requested_at}"
