# hotel_backup/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class HotelBackupManager(models.Model):
    class Meta:
        managed = False
        verbose_name = _('مدیریت بکاپ و ریستور هتل‌ها')
        verbose_name_plural = _('مدیریت بکاپ و ریستور هتل‌ها')