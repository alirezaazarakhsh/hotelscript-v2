from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)

AVAILABLE_PAGES = (
    ('home', 'صفحه اصلی'),
    ('about', 'درباره ما'),
    ('contact', 'تماس با ما'),
    ('magazine', 'مجله گردشگری'),
    ('best-hotels', 'بهترین هتل‌ها'),
)

AVAILABLE_SECTIONS = (
    ('recommended-hotels', 'هتل‌های پیشنهادی'),
    ('popular-cities', 'شهرهای پربازدید'),
    ('incredible-hotels', 'هتل‌های شگفت‌انگیز'),
    ('best-selling-hotels', 'هتل‌های پرفروش'),
    ('top-hotels', 'هتل‌های برتر'),
    ('enaging-blogs', 'بلاگ های جذاب'),
    ('customer-reviews', 'نظرات مشتریان'),
    ('contact-us', 'تماس با ما'),
    ('social-media', 'سوشال مدیا'),
    ('contact-form', 'فرم تماس با ما'),
)

# Create your models here.
class Page(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )
    page = models.CharField(
        verbose_name=_('صفحه'),
        choices=AVAILABLE_PAGES,
        max_length=32,
        unique=True,
    )
    path = models.CharField(
        max_length=255,
        validators=(
            RegexValidator(
                regex=r'^[a-zA-Z0-9\-_/]*$',
                message='مقدار مسیر تنها میتواند شامل حروف و اعداد انگلیسی، - و _ و / باشد.'
            ),
        ),
        unique=True,
    )

    class Meta:
        verbose_name = 'صفحه'
        verbose_name_plural = 'صفحات'

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.path.startswith('/'):
            self.path = '/' + self.path
        super(Page, self).save(*args, **kwargs)
    
class HeaderMenu(models.Model):
    MAX_ALLOWED_INSTANCES = 5

    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
        unique=True,
        validators=(
            MinValueValidator(1),
            MaxValueValidator(5),
        )
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )
    page = models.OneToOneField(
        Page,
        verbose_name=_('صفحه'),
        on_delete=models.CASCADE,
        related_name='header_menu'
    )

    class Meta:
        verbose_name = 'منوی هدر'
        verbose_name_plural = 'منوهای هدر'
        ordering = ('order',)
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk is None and HeaderMenu.objects.count() >= HeaderMenu.MAX_ALLOWED_INSTANCES:
            raise ValidationError(f'تنها به تعداد${HeaderMenu.MAX_ALLOWED_INSTANCES} منوی هدر میتوانید بسازید.')

        if self.pk:
            current_instance = HeaderMenu.objects.get(pk=self.pk)
            if current_instance.order != self.order:
                if current_instance.order < self.order:
                    HeaderMenu.objects.filter(order__gt=current_instance.order, order__lte=self.order).update(order=models.F('order') - 1)
                else:
                    HeaderMenu.objects.filter(order__lt=current_instance.order, order__gte=self.order).update(order=models.F('order') + 1)

        super().save(*args, **kwargs)

class QuickAccess(models.Model):
    MAX_ALLOWED_INSTANCES = 5

    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
        unique=True,
        validators=(
            MinValueValidator(1),
            MaxValueValidator(5),
        )
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
        unique=True,
    )
    page = models.OneToOneField(
        Page,
        verbose_name=_('صفحه'),
        on_delete=models.CASCADE,
        related_name='quick_access'
    )

    class Meta:
        verbose_name = 'دسترسی سریع'
        verbose_name_plural = 'دسترسی‌های سریع'
        ordering = ('order',)
    
    def __str__(self):
        return f'{self.order}. {self.title}'

    def save(self, *args, **kwargs):
        if self.pk is None and QuickAccess.objects.count() >= QuickAccess.MAX_ALLOWED_INSTANCES:
            raise ValidationError(f'تنها به تعداد${QuickAccess.MAX_ALLOWED_INSTANCES} دسترسی سریع میتوانید بسازید.')

        if self.pk:
            current_instance = QuickAccess.objects.get(pk=self.pk)
            if current_instance.order != self.order:
                if current_instance.order < self.order:
                    QuickAccess.objects.filter(order__gt=current_instance.order, order__lte=self.order).update(order=models.F('order') - 1)
                else:
                    QuickAccess.objects.filter(order__lt=current_instance.order, order__gte=self.order).update(order=models.F('order') + 1)

        super().save(*args, **kwargs)

class Section(models.Model):
    section = models.CharField(
        verbose_name=_('بخش'),
        choices=AVAILABLE_SECTIONS,
        max_length=64,
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    sub_title = models.CharField(
        verbose_name=_('زیر عنوان'),
        max_length=256,
    )
    page = models.OneToOneField(
        Page,
        verbose_name=_('صفحه'),
        on_delete=models.CASCADE,
        related_name='sections'
    )

    class Meta:
        verbose_name = 'بخش'
        verbose_name_plural = 'بخش‌ها'
        constraints = (
            models.UniqueConstraint(
                fields=('section', 'page'),
                name='unique_section_page'
            ),
        )
    
    def __str__(self):
        return f'{self.title} - {self.page}'
