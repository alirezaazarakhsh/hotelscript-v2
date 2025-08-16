# config/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        from .models import Media

        @receiver(post_delete, sender=Media)
        def delete_media_file(sender, instance, **kwargs):
            if instance.file and os.path.isfile(instance.file.path):
                os.remove(instance.file.path)
