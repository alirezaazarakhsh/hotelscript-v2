from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import os
import logging
from .models import Media, Folder, Slide, Banner  # مدل‌های دیگر را اضافه کنید

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Media)
def handle_media_upload(sender, instance, created, **kwargs):
    if created and instance.file:
        file_path = instance.file.name
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
        # بررسی ارجاعات فایل در مدل‌های دیگر
        file_path = instance.file.name
        is_referenced = False
        # بررسی مدل‌های دیگر که ممکن است به فایل ارجاع دهند
        for model in [Slide, Banner]:  # مدل‌های دیگر را اضافه کنید
            if model.objects.filter(file=file_path).exists():  # فرض کنید فیلد file دارند
                is_referenced = True
                logger.info(f"فایل {file_path} در مدل {model.__name__} استفاده شده و حذف نمی‌شود.")
                break
        # اگر فایل در جای دیگری استفاده نشده، حذف شود
        if not is_referenced:
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