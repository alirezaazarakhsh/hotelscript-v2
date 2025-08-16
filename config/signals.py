from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

class Media(models.Model):
    file = models.FileField(verbose_name="فایل", upload_to="media/")

    def admin_file(self):
        if self.file:
            return mark_safe(f'<img src="{self.file.url}" width="100" />')
        return "بدون فایل"
    admin_file.short_description = "عکس"

    def __str__(self) -> str:
        return self.file.name if self.file else "فایل ندارد"

    class Meta:
        verbose_name = "رسانه"
        verbose_name_plural = "رسانه ها"


@receiver(post_delete, sender=Media)
def delete_media_file(sender, instance, **kwargs):
    """
    وقتی رکورد پاک شد، فایل فیزیکی هم پاک بشه
    """
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)
