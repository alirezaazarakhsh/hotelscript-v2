from django.db.models.signals import post_save
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
        folder_name = os.path.dirname(file_path).strip('/')
        if folder_name:
            folder, _ = Folder.objects.get_or_create(name=folder_name)
            instance.folder = folder
            instance.save()
            logger.info(f"فایل {file_path} در پوشه {folder_name} ثبت شد.")
        else:
            logger.info(f"فایل {file_path} در پوشه root ثبت شد.")