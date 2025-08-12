# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Media, Folder

@receiver(post_save)
def handle_media_upload(sender, instance, created, **kwargs):
    # بررسی اینکه مدل واقعاً Media هست
    if sender is Media:
        if created:
            print(f"فایل جدید آپلود شد: {instance.file.name}")
            # اینجا می‌تونی پوشه رو هم اتوماتیک ست کنی
            if not instance.folder:
                default_folder, _ = Folder.objects.get_or_create(name='پیش‌فرض')
                instance.folder = default_folder
                instance.save(update_fields=['folder'])
