from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import os
import logging
from .models import Media, Folder

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Media)
def handle_media_upload(sender, instance, created, **kwargs):
    if created and instance.file:
        file_path = instance.file.name
        # نرمال‌سازی مسیر فایل
        clean_file_path = file_path
        while clean_file_path.startswith('media/'):
            clean_file_path = clean_file_path[len('media/'):]
        folder_name = os.path.dirname(clean_file_path).strip('/')
        if folder_name:
            folder, _ = Folder.objects.get_or_create(name=folder_name)
            instance.folder = folder
            instance.save(update_fields=['folder'])
            logger.info(f"فایل {file_path} در پوشه {folder_name} ثبت شد.")
        else:
            logger.info(f"فایل {file_path} در پوشه root ثبت شد.")

@receiver(post_delete, sender=Media)
def handle_media_delete(sender, instance, **kwargs):
    if instance.file and os.path.exists(instance.file.path):
        try:
            os.remove(instance.file.path)
            logger.info(f"فایل {instance.file.path} از سرور حذف شد.")
            # حذف پوشه خالی در صورت وجود
            folder_path = os.path.dirname(instance.file.path)
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                logger.info(f"پوشه خالی {folder_path} حذف شد.")
        except Exception as e:
            logger.error(f"خطا در حذف فایل {instance.file.path}: {str(e)}")