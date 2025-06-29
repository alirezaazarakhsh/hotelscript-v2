# notification/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_jalali.db import models as jmodels
from authentication.models import BaseUser

class Notification(models.Model):
    class StatusChoices(models.TextChoices):
        NEW = 'new', _('جدید')
        IMPORTANT = 'important', _('مهم')

    title = models.CharField(max_length=255, verbose_name=_("عنوان"))
    message = models.TextField(verbose_name=_("متن اعلان"))
    users = models.ManyToManyField(
        BaseUser,
        related_name='notifications',
        verbose_name=_("کاربران"),
        blank=True,
    )
    
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NEW,
        verbose_name=_("وضعیت")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد میلادی"))
    created_date_jalali = jmodels.jDateField(auto_now_add=True, verbose_name=_("تاریخ شمسی"))
    created_time = models.TimeField(auto_now_add=True, verbose_name=_("ساعت"))

    send_to_all = models.BooleanField(default=False, verbose_name=_("ارسال برای همه"))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.send_to_all and is_new:
            all_users = BaseUser.objects.all()
            self.users.set(all_users)

    def get_users_with_names(self):
        result = []
        for user in self.users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def __str__(self):
        return f"{self.title} - {self.status}"

    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان ها'
