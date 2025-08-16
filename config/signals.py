import os
import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from config.models import (
    Media, Folder, Slide, SiteConfig, Statistic, ChooseReason, 
    Service, Banner, License, FakeComment, ComingSoon
)
from reservation.models import HotelGallery
from .models import FileReference  # اگر از مدل FileReference استفاده می‌کنید

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Media)
def handle_media_upload(sender, instance, created, **kwargs):
    """
    هنگام آپلود فایل جدید در Media، پوشه مناسب رو تخصیص بده.
    """
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
    """
    هنگام حذف Media، فایل فیزیکی رو فقط اگه هیچ مدل دیگه‌ای بهش ارجاع نداره پاک کن.
    همچنین FileReferenceهای مرتبط و فیلدهای مدل‌های دیگر رو آپدیت کن.
    """
    if instance.file and os.path.isfile(instance.file.path):
        file_path = instance.file.name
        is_referenced = False

        # بررسی مدل‌های دیگر که ممکنه به فایل ارجاع بدن
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
                # بررسی FileFieldهای مدل‌ها
                if model.objects.filter(**{field_name: file_path}).exists():
                    is_referenced = True
                    logger.info(f"فایل {file_path} در مدل {model.__name__} (فیلد {field_name}) استفاده شده و حذف نمی‌شود.")
                    break
            except AttributeError:
                logger.warning(f"مدل {model.__name__} یا فیلد {field_name} وجود ندارد.")

        # بررسی FileReference (اگر استفاده می‌کنید)
        if FileReference.objects.filter(media=instance).exists():
            is_referenced = True
            logger.info(f"فایل {file_path} در FileReference استفاده شده و حذف نمی‌شود.")

        # اگر فایل جایی استفاده نشده، حذفش کن
        if not is_referenced:
            try:
                os.remove(instance.file.path)
                logger.info(f"فایل {instance.file.path} از سرور حذف شد.")
                # حذف پوشه خالی
                folder_path = os.path.dirname(instance.file.path)
                if os.path.exists(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
                    logger.info(f"پوشه خالی {folder_path} حذف شد.")
            except Exception as e:
                logger.error(f"خطا در حذف فایل {instance.file.path}: {str(e)}")

        # آپدیت مدل‌های مرتبط (null کردن فیلدها)
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
                model.objects.filter(**{field_name: file_path}).update(**{field_name: None})
                logger.info(f"فیلد {field_name} در مدل {model.__name__} به null تنظیم شد.")
            except AttributeError:
                logger.warning(f"مدل {model.__name__} یا فیلد {field_name} وجود ندارد.")

        # حذف FileReferenceهای مرتبط
        FileReference.objects.filter(media=instance).delete()
        logger.info(f"FileReferenceهای مرتبط با {file_path} حذف شدند.")

@receiver(pre_save)
def track_file_field_changes(sender, instance, **kwargs):
    """
    ردیابی تغییرات FileField در همه مدل‌ها و ثبت در Media و FileReference.
    """
    if sender in (Media, Folder, FileReference):  # مدل‌های خودمون رو نادیده بگیر
        return

    for field in instance._meta.get_fields():
        if isinstance(field, (models.FileField, models.ImageField)):
            file = getattr(instance, field.name)
            if file and file.name:
                # ثبت یا پیدا کردن Media
                media, created = Media.objects.get_or_create(
                    file=file.name,
                    defaults={'folder': None}
                )
                if created:
                    logger.info(f"رکورد Media برای فایل {file.name} ساخته شد.")
                # ثبت در FileReference
                if instance.pk:  # فقط اگه instance ذخیره شده باشه
                    content_type = ContentType.objects.get_for_model(instance)
                    FileReference.objects.update_or_create(
                        content_type=content_type,
                        object_id=instance.pk,
                        defaults={'media': media}
                    )
                    logger.info(f"FileReference برای {file.name} در {sender.__name__} ثبت شد.")
            else:
                # اگر فایل null شده، FileReference رو پاک کن
                if instance.pk:
                    content_type = ContentType.objects.get_for_model(instance)
                    FileReference.objects.filter(
                        content_type=content_type,
                        object_id=instance.pk
                    ).delete()
                    logger.info(f"FileReference برای {sender.__name__} حذف شد.")