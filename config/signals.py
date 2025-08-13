from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import os
import logging
from config.models import (
    Media, Folder, Slide, SiteConfig, Statistic, ChooseReason, 
    Service, Banner, License, FakeComment, ComingSoon
)
from reservation.models import HotelGallery

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
        file_path = instance.file.name
        is_referenced = False
        # بررسی مدل‌های دیگر که ممکن است به فایل ارجاع دهند
        for model, field_name in [
            (SiteConfig, 'header_logo'),
            (SiteConfig, 'footer_logo'),
            (Slide, 'image'),
            (Statistic, 'image'),
            (ChooseReason, 'image'),
            (Service, 'image'),
            (Banner, 'image'),
            (License, 'image'),
            (FakeComment, 'commenter_image'),
            (ComingSoon, 'logo'),
            (ComingSoon, 'background'),
            (HotelGallery, 'image'),
        ]:
            try:
                if model.objects.filter(**{field_name: file_path}).exists():
                    is_referenced = True
                    logger.info(f"فایل {file_path} در مدل {model.__name__} (فیلد {field_name}) استفاده شده و حذف نمی‌شود.")
                    break
            except AttributeError:
                logger.warning(f"مدل {model.__name__} یا فیلد {field_name} وجود ندارد.")
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