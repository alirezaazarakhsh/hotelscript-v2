from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

def validate_svg(file):
    if not file.name.lower().endswith('.svg'):
        raise ValidationError(_("فقط فایل‌های SVG مجاز هستند."))

class IconShortcut(models.Model):
    order = models.PositiveIntegerField(
        verbose_name=_("ترتیب"),
        unique=True,
        help_text=_("ترتیب نمایش آیکون")
    )
    title_icon = models.CharField(
        verbose_name=_("عنوان آیکون"),
        max_length=128,
        help_text=_("نام یا عنوان آیکون")
    )
    svg_icon = models.FileField(
        verbose_name=_("فایل آیکون SVG"),
        upload_to="icons/svg_icons/",
        validators=[validate_svg],
        help_text=_("فایل با فرمت SVG آپلود کنید")
    )

    class Meta:
        verbose_name = _("آیکون ")
        verbose_name_plural = _("آیکون‌ها")
        ordering = ['order']

    def __str__(self):
        return f"{self.order} - {self.title_icon}"
