from django.core.management.base import BaseCommand
from config.models import Media
import os
import shutil

# مسیر اپ اصلی که فایل‌ها داخلش هستند
APP_MEDIA_DIR = '/var/hotelscript-v2/media/'  # مسیر اپ اصلی

class Command(BaseCommand):
    help = "همگام‌سازی فایل‌های اپ اصلی با مدل Media"

    def handle(self, *args, **kwargs):
        created_count = 0

        # لیست همه فایل‌های داخل اپ اصلی
        for root, dirs, files in os.walk(APP_MEDIA_DIR):
            for filename in files:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, APP_MEDIA_DIR)

                # چک کن ببین این فایل توی مدل Media هست یا نه
                if not Media.objects.filter(file=f"media/{relative_path}").exists():
                    # فایل رو به مدل اضافه کن
                    media_instance = Media.objects.create(file=f"media/{relative_path}")
                    self.stdout.write(f"Added {media_instance.file}")
                    created_count += 1

        self.stdout.write(f"✅ {created_count} فایل جدید به Media اضافه شد.")
