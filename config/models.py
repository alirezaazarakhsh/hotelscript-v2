from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from .managers import ActiveManager
from .validators import (
    validate_future_datetime,
)

AVAILABLE_PAGES = (
    ('home', 'صفحه اصلی'),
    ('about', 'درباره ما'),
    ('contact', 'تماس با ما'),
    ('magazine', 'مجله گردشگری'),
    ('best-hotels', 'بهترین هتل‌ها'),
    ('rules', 'قوانین'),
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

# مدل اضافه کردن صفحه جدید در پروژه 
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
    
    
    
    
# مدل منوی هدر 
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
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/sections/',
        null=True,
        blank=True,
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
        null=True,
        blank=True,
    )
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        verbose_name=_('صفحه'),
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



# مدل کانفیگ سایت 
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
    footer_copyright = models.CharField(
        verbose_name=_('کپی‌رایت فوتر'),
        max_length=128,
        help_text=_('متن کپی‌رایت که در پایین فوتر نمایش داده می‌شود'),
        blank=True,
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




#مدل بنر های وب سایت 
class Slide(models.Model):
    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
        unique=True,
    )
    
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/slides/',
    )
    
    is_active = models.BooleanField(
        verbose_name=_('فعال'),
        default=True,
    )

    objects = models.Manager()
    actives = ActiveManager()

    class Meta:
        verbose_name = 'اسلاید'
        verbose_name_plural = 'اسلایدهای صفحه اصلی'
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





# مدل کانفیگ درباره ما
class Statistic(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان اصلی'),
        max_length=64,
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
        blank=True,
        null=True,
    )
    image = models.ImageField(
        verbose_name=_('تصویر'),
        upload_to='about_us/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'کانفیگ درباره ما'
        verbose_name_plural = 'کانفیگ درباره ما'

    def __str__(self):
        return self.title


class StatisticItem(models.Model):
    statistic = models.ForeignKey(
        Statistic,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='مربوط به',
    )
    title = models.CharField(
        verbose_name=_('عنوان آیتم'),
        max_length=64,
    )
    subtitle = models.CharField(
        verbose_name=_('زیرعنوان آیتم'),
        max_length=128,
    )

    class Meta:
        verbose_name = 'آیتم آماری'
        verbose_name_plural = 'آیتم‌های آماری'

    def __str__(self):
        return self.title



# مدل دلایل انتخاب 
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
        verbose_name_plural = 'دلایل انتخاب درباره ما'
    
    def __str__(self):
        return self.title




#مدل سوالات متداول بر اساس هر پیج 
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
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        verbose_name=_('صفحه'),
        related_name='faqs',
    )

    class Meta:
        verbose_name = 'سوال متداول'
        verbose_name_plural = 'سوالات متداول صفحات'
    
    def __str__(self):
        return self.question




# مدل خدمات درباره ما
class Service(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=128,
    )
    description = models.TextField(
        verbose_name=_('توضیحات')
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/services/'
    )

    class Meta:
        verbose_name = 'خدمت'
        verbose_name_plural = 'خدمات درباره ما'
    
    def __str__(self):
        return self.title




# مدل راه های ارتباطی برای صفحه تماس با ما و بخشی از فوتر 
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



# مدل شبکه های احتماعی در تماس با ما و فوتر 
class SocialMedia(models.Model):
    type = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        choices=SOCIAL_MEDIA_OPTIONS
    )
    type_fa = models.CharField(
        verbose_name=_('عنوان فارسی'),
        max_length=64,
        blank=True,
        null=True,
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=1024,
        unique=True,
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
        verbose_name = 'شبکه اجتماعی'
        verbose_name_plural = 'شبکه‌های اجتماعی'
    
    def __str__(self):
        return self.link

    
    

# مدل اضافه کردن بنر در صفحات 
class Banner(models.Model):
    order = models.PositiveSmallIntegerField(
        verbose_name=_('ترتیب'),
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/banners/',
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=512,
        null=True,
        blank=True,
    )
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        verbose_name=_('صفحه'),
        related_name='banners',
    )

    class Meta:
        verbose_name = 'بنر'
        verbose_name_plural = 'بنرها'
        ordering = ('order',)
        constraints = (
            models.UniqueConstraint(
                fields=('order', 'page'),
                name='unique_order_page'
            ),
        )
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            current_instance = Banner.objects.get(pk=self.pk)
            if current_instance.order != self.order:
                if current_instance.order < self.order:
                    Banner.objects.filter(page=self.page, order__gt=current_instance.order, order__lte=self.order).update(order=models.F('order') - 1)
                else:
                    Banner.objects.filter(page=self.page, order__lt=current_instance.order, order__gte=self.order).update(order=models.F('order') + 1)

        super().save(*args, **kwargs)




# مدل کد اینماد در فوتر 
class EnamadLicense(models.Model):
    code = models.TextField(
        verbose_name=_('کد اینماد'),
    )

    class Meta:
        verbose_name = 'کد اینماد'
        verbose_name_plural = 'کد اینماد'
    
    def __str__(self):
        return f'کد اینماد'
    
    def save(self, *args, **kwargs):
        if not self.pk and EnamadLicense.objects.exists():
            raise ValidationError('تنها یک کد اینماد میتوانید بسازید!')
        return super(EnamadLicense, self).save(*args, **kwargs)



# مدل اضافه کردن مجوز در فوتر 
class License(models.Model):
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/licenses/',
    )
    link = models.URLField(
        verbose_name=_('لینک'),
        max_length=512,
    )

    class Meta:
        verbose_name = 'مجوز'
        verbose_name_plural = 'مجوزها'
    
    def __str__(self):
        return f'{self.link}'

class Advantage(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    subtitle = models.CharField(
        verbose_name=_('زیر عنوان'),
        max_length=256,
    )
    icon = models.CharField(
        verbose_name=_('آیکن'),
        max_length=64,
    )
    
    class Meta:
        verbose_name = 'مزیت'
        verbose_name_plural = 'مزایا'
    
    def __str__(self):
        return f'{self.title}'

class FakeComment(models.Model):
    commenter = models.CharField(
        verbose_name=_('نام و نام خانوادگی نظردهنده'),
        max_length=64,
    )
    commenter_image = models.ImageField(
        verbose_name=_('پروفایل نظردهنده'),
        upload_to='images/comments/profiles',
    )
    evaluation = models.CharField(
        verbose_name=_('ارزیابی'),
        max_length=32,
    )
    text = models.CharField(
        verbose_name=_('نظر'),
        max_length=512,
    )
    rate = models.DecimalField(
        verbose_name=_('امتیاز'),
        max_digits=3,
        decimal_places=1,
        validators=(
            MinValueValidator(Decimal(0.0)),
            MaxValueValidator(Decimal(5.0)),
        )
    )
    
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات مشتریان صفحه اصلی '
    
    def __str__(self):
        return f'{self.commenter}'



class Rule(models.Model):
    tab_title = models.CharField(
        verbose_name=_('عنوان تب'),
        max_length=32,
    )
    text = models.TextField(
        verbose_name=_('متن'),
    )

    class Meta:
        verbose_name = 'قانون'
        verbose_name_plural = 'قوانین'
    
    def __str__(self):
        return f'{self.tab_title}'

class ComingSoon(models.Model):
    logo = models.ImageField(
        verbose_name=_('لوگو'),
        upload_to='images/coming-soon',
    )
    background = models.ImageField(
        verbose_name=_('پس زمینه'),
        upload_to='images/coming-soon',
    )
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
    )
    subtitle = models.CharField(
        verbose_name=_('زیرعنوان'),
        max_length=128,
    )
    end_date = models.DateTimeField(
        verbose_name=_('تاریخ'),
        validators=(
            validate_future_datetime,
        )
    )
    copyright_text = models.CharField(
        verbose_name=_('متن کپی رایت'),
        max_length=128,
    )
    is_active = models.BooleanField(
        verbose_name=_('فعال'),
        default=True,
    )
    class Meta:
        verbose_name = 'کامینگ سون'
        verbose_name_plural = 'کامینگ سون '
    
    def __str__(self):
        return f'کامینگ سون'
    
    def save(self, *args, **kwargs):
        if not self.pk and ComingSoon.objects.exists():
            raise ValidationError('تنها یک کامینگ سون برای سایت میتوانید بسازید!')
        return super(ComingSoon, self).save(*args, **kwargs)




class UserLevel(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    icon = models.CharField(
        verbose_name=_('آیکن'),
        max_length=64,
    )
    
    class Meta:
        verbose_name = 'سطح کاربری'
        verbose_name_plural = 'سطوح کاربری'
    
    def __str__(self):
        return f'{self.title}'
