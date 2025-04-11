from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class StoryCategory(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    thumbnail = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/story-categories/',
    )
    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
        unique=True,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'دسته استوری'
        verbose_name_plural = 'دسته‌های استوری'
        ordering = ('order',)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            current_instance = self.objects.get(pk=self.pk)
            if current_instance.order != self.order:
                if current_instance.order < self.order:
                    self.objects.filter(order__gt=current_instance.order, order__lte=self.order).update(order=models.F('order') - 1)
                else:
                    self.objects.filter(order__lt=current_instance.order, order__gte=self.order).update(order=models.F('order') + 1)

        super().save(*args, **kwargs)
