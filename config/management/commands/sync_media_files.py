from django.core.management.base import BaseCommand
from django.conf import settings
import os
from config.models import Media, Folder
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'ثبت فایل‌های موجود در MEDIA_ROOT در دیتابیس و همگام‌سازی'

    def handle(self, *args, **kwargs):
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            self.stdout.write(self.style.ERROR(f"پوشه MEDIA_ROOT وجود ندارد: {media_root}"))
            return

        # ثبت فایل‌های موجود در MEDIA_ROOT
        for root, _, files in os.walk(media_root):
            relative_folder = os.path.relpath(root, media_root)
            folder_name = relative_folder if relative_folder != '.' else 'root'
            if folder_name == 'root' and not files:
                continue

            folder, _ = Folder.objects.get_or_create(name=folder_name)
            for file_name in files:
                relative_path = os.path.join(relative_folder, file_name).replace('\\', '/')
                if not Media.objects.filter(file=relative_path).exists():
                    Media.objects.create(file=relative_path, folder=folder)
                    self.stdout.write(self.style.SUCCESS(f"فایل {relative_path} در پوشه {folder_name} ثبت شد."))
                else:
                    self.stdout.write(self.style.WARNING(f"فایل {relative_path} قبلاً ثبت شده است."))

        # حذف فایل‌هایی که در دیتابیس هستند اما در MEDIA_ROOT وجود ندارند
        for media in Media.objects.all():
            if not os.path.exists(media.file.path):
                try:
                    media.delete()
                    self.stdout.write(self.style.WARNING(f"رکورد {media.file} از دیتابیس حذف شد زیرا فایل وجود ندارد."))
                except Exception as e:
                    logger.error(f"خطا در حذف رکورد {media.file}: {str(e)}")