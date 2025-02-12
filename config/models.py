from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from .managers import ActiveManager

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
    ('about-us', 'درباره ما'),
    ('why-choose-us?', 'دلایل انتخاب'),
    ('faq', 'سوالات متداول'),
    ('services-at-a-glance', 'نگاهی به خدمات'),
)

SOCIAL_MEDIA_OPTIONS = (
    ('telegram', 'Telegram'),
    ('instagram', 'Instagram'),
    ('linkedin', 'LinkedIn'),
    ('youtube', 'YouTube'),
    ('facebook', 'Facebook'),
    ('discord', 'Discord'),
    ('x', 'X'),
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
            raise ValidationError(f'تنها به تعداد {HeaderMenu.MAX_ALLOWED_INSTANCES} منوی هدر میتوانید بسازید.')

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
            raise ValidationError(f'تنها به تعداد {QuickAccess.MAX_ALLOWED_INSTANCES} دسترسی سریع میتوانید بسازید.')

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

class SiteConfig(models.Model):
    header_logo = models.ImageField(
        verbose_name=_('لوگوی هدر'),
        upload_to='images/logo/'
    )
    header_title = models.CharField(
        verbose_name=_('عنوان هدر'),
        max_length=32,
    )
    header_sub_title = models.CharField(
        verbose_name=_('زیر عنوان هدر'),
        max_length=64,
    )
    footer_logo = models.ImageField(
        verbose_name=_('لوگوی فوتر'),
        upload_to='images/logo/',
    )
    footer_title = models.CharField(
        verbose_name=_('عنوان فوتر'),
        max_length=32,
    )
    footer_description = models.TextField(
        verbose_name=_('توضیحات فوتر'),
    )

    class Meta:
        verbose_name = 'کانفیگ سایت'
        verbose_name_plural = 'کانفیگ سایت'
    
    def __str__(self):
        return f'کانفیگ سایت {self.header_title}'
    
    def save(self, *args, **kwargs):
        if not self.pk and SiteConfig.objects.exists():
            raise ValidationError('تنها یک کانفیگ برای سایت میتوانید بسازید!')
        return super(SiteConfig, self).save(*args, **kwargs)

class Slide(models.Model):
    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
        unique=True,
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/slides/',
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=512,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        verbose_name=_('فعال'),
        default=True,
    )

    objects = models.Manager()
    actives = ActiveManager()

    class Meta:
        verbose_name = 'اسلاید'
        verbose_name_plural = 'اسلایدها'
        ordering = ('order',)
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            current_instance = Slide.objects.get(pk=self.pk)
            if current_instance.order != self.order:
                if current_instance.order < self.order:
                    Slide.objects.filter(order__gt=current_instance.order, order__lte=self.order).update(order=models.F('order') - 1)
                else:
                    Slide.objects.filter(order__lt=current_instance.order, order__gte=self.order).update(order=models.F('order') + 1)

        super().save(*args, **kwargs)

class Statistic(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
    )
    subtitle = models.CharField(
        verbose_name=_('زیرعنوان'),
        max_length=64,
    )

    class Meta:
        verbose_name = 'آمار و ارقام'
        verbose_name_plural = 'آمار و ارقام'
    
    def __str__(self):
        return self.title

class ChooseReason(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=32,
    )
    description = models.CharField(
        verbose_name=_('توضیحات'),
        max_length=450,
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/why-choose-us/',
    )

    class Meta:
        verbose_name = 'دلیل انتخاب'
        verbose_name_plural = 'دلایل انتخاب'
    
    def __str__(self):
        return self.title

class FAQ(models.Model):
    question = models.TextField(
        verbose_name=_('سوال'),
    )
    answer = models.TextField(
        verbose_name=_('جواب')
    )
    icon = models.CharField(
        verbose_name=_('آیکن'),
        max_length=64,
    )

    class Meta:
        verbose_name = 'سوال متداول'
        verbose_name_plural = 'سوالات متداول'
    
    def __str__(self):
        return self.question

class Service(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    description = models.TextField(
        verbose_name=_('توضیحات')
    )

    class Meta:
        verbose_name = 'خدمت'
        verbose_name_plural = 'خدمات'
    
    def __str__(self):
        return self.title

class ContactInfo(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    subtitle = models.CharField(
        verbose_name=_('زیرعنوان'),
        max_length=128,
    )
    value = models.CharField(
        verbose_name=_('مقدار'),
        max_length=64,
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=1024,
        blank=True,
        null=True,
    )
    icon = models.CharField(
        verbose_name=_('آیکن'),
        max_length=64,
    )
    show_in_footer = models.BooleanField(
        verbose_name=_('نمایش در فوتر'),
        default=False,
    )

    class Meta:
        verbose_name = 'راه ارتباطی'
        verbose_name_plural = 'راه‌های ارتباطی'
    
    def __str__(self):
        return self.title

class SocialMedia(models.Model):
    type = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        choices=SOCIAL_MEDIA_OPTIONS
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=1024,
        unique=True,
    )
    show_in_footer = models.BooleanField(
        verbose_name=_('نمایش در فوتر'),
        default=False,
    )

    class Meta:
        verbose_name = 'شبکه اجتماعی'
        verbose_name_plural = 'شبکه‌های اجتماعی'
    
    def __str__(self):
        return self.link

