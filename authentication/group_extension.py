from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext_lazy as _
from icons.models import IconShortcut


class GroupExtension(models.Model):
    """
    افزودن فیلدهای اضافی به Group برای گروه‌بندی اپلیکیشن‌ها
    """
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='extension',
        verbose_name=_('گروه')
    )
    icon = models.ForeignKey(
        IconShortcut,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('آیکون'),
        help_text=_('آیکون این گروه')
    )
    order = models.IntegerField(
        default=0,
        verbose_name=_('ترتیب نمایش'),
        help_text=_('عدد کوچکتر = اولویت بالاتر')
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('نام نمایشی'),
        help_text=_('نام فارسی گروه برای نمایش')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('توضیحات'),
    )

    class Meta:
        verbose_name = "گروه اپلیکیشن"
        verbose_name_plural = "گروه‌های اپلیکیشن"
        ordering = ['order', 'group__name']

    def __str__(self):
        return self.display_name or self.group.name
