from django.core.management.base import BaseCommand
from config.models import Media  # چون مدل توی config هست
import os

class Command(BaseCommand):
    help = "پاک کردن رکوردهای Media که فایلشون وجود نداره"

    def handle(self, *args, **kwargs):
        deleted_count = 0
        for media in Media.objects.all():
            if not os.path.exists(media.file.path):
                self.stdout.write(f"Deleting {media} (file missing)")
                media.delete()
                deleted_count += 1
        self.stdout.write(f"✅ {deleted_count} رکورد حذف شد.")
