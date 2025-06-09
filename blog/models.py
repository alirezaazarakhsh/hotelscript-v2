from django.utils import timezone
from ckeditor.fields import RichTextField
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_jalali.db import models as jmodels
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)
from authentication.models import Admin
from reservation.models import Hotel
from .managers import (
    HasStoryManager,
    PublishedManager,
    PublishingManager,
    ApprovedManager,
)

# Create your models here.

# مدل دسته بندی استوری وبلاگ
class StoryCategory(models.Model):
    title = models.CharField(
        verbose_name=_('عنوان'),
        max_length=64,
        unique=True,
    )
    thumbnail = models.ImageField(
        verbose_name=_('عکس کاور دسته بندی'),
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

    objects = models.Manager()
    has_story = HasStoryManager()

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



# مدل استوری وبلاگ
class Story(models.Model):
    image = models.ImageField(
        verbose_name=_('عکس'),
        upload_to='images/stories/',
    )
    category = models.ForeignKey(
        StoryCategory,
        on_delete=models.CASCADE,
        verbose_name=_('دسته بندی'),
        related_name='stories',
    )
    
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        verbose_name=_('هتل'),
        related_name='stories',
        null=True,
    )
    

    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'استوری'
        verbose_name_plural = 'استوری‌ها'
        ordering = ('created',)

    def __str__(self):
        return f'{self.category}-{self.pk}'



# مدل دسته بندی مقالات
class ArticleCategory(models.Model):
    title = models.CharField(
        max_length=256,
        verbose_name=_('عنوان'),
        unique=True,
    )
    slug = models.SlugField(
        max_length=256,
        verbose_name=_('اسلاگ'),
        unique=True,
        allow_unicode=True,
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
        blank=True,
    )
    articles = GenericRelation('Article')

    class Meta:
        verbose_name = 'دسته‌بندی اصلی مقالات'
        verbose_name_plural = 'دسته‌بندی‌های اصلی مقالات'

    def __str__(self):
        return self.title


# مدل دسته بندی فرعی مقالات
class ArticleSubCategory(models.Model):
    title = models.CharField(
        max_length=256,
        verbose_name=_('عنوان'),
    )
    slug = models.SlugField(
        max_length=256,
        verbose_name=_('اسلاگ'),
        unique=True,
        allow_unicode=True,
    )
    description = models.TextField(
        verbose_name=_('توضیحات'),
        blank=True,
    )
    parent = models.ForeignKey(
        ArticleCategory,
        on_delete=models.CASCADE,
        verbose_name=_('دسته‌بندی اصلی'),
        related_name='subcategories',
    )
    articles = GenericRelation('Article')

    class Meta:
        verbose_name = 'دسته‌بندی فرعی مقالات'
        verbose_name_plural = 'دسته‌بندی‌های فرعی مقالات'
        unique_together = (
            'title',
            'parent',
        )

    def __str__(self):
        return self.title



#مدل برچسب های مقالات
class ArticleTag(models.Model):
    title = models.CharField(
        max_length=256,
        verbose_name=_('عنوان'),
        unique=True,
    )
    class Meta:
        verbose_name = 'تگ'
        verbose_name_plural = 'تگ‌ها'

    def __str__(self):
        return self.title





#مدل مقاله
class Article(models.Model):
    ARTICLE_STATUSES = (
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('inactive', 'غیرفعال'),
    )

    def article_thumbnail_upload_to(instance, filename):
        try:
            return f'images/articles/{instance.slug}/{filename}'
        except:
            return f'images/articles/default/{filename}'

    title = models.CharField(
        max_length=256,
        verbose_name=_('عنوان'),
        unique=True,
    )
    slug = models.SlugField(
        max_length=256,
        verbose_name=_('اسلاگ'),
        unique=True,
        allow_unicode=True,
    )
    summary = models.TextField(
    verbose_name=_('خلاصه مقاله'),
    max_length=512,
    blank=True,
    null=True,
    )
    body = RichTextField(
        verbose_name=_('متن'),
    )
    author = models.ForeignKey(
        Admin,
        on_delete=models.CASCADE,
        verbose_name=_('نویسنده'),
        related_name='articles',
    )
    category_content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={
            'model__in': [
                'articlecategory',
                'articlesubcategory',
            ],
            'app_label': 'blog',
        },
        on_delete=models.CASCADE,
        verbose_name=_('دسته‌بندی'),
    )
    category_object_id = models.PositiveIntegerField()
    category = GenericForeignKey(
        'category_content_type',
        'category_object_id',
    )
    tags = models.ManyToManyField(
        ArticleTag,
        verbose_name=_('تگ'),
        related_name='articles',
    )
    thumbnail = models.ImageField(
        verbose_name=_('تصویر پیش‌نمایش'),
        upload_to=article_thumbnail_upload_to,
    )
    view_count = models.PositiveBigIntegerField(
        verbose_name=_('تعداد بازدید'),
        default=0,
    )
    status = models.CharField(
        verbose_name=_('وضعیت'),
        max_length=16,
        choices=ARTICLE_STATUSES,
        default='draft',
    )
    is_popular = models.BooleanField(
        verbose_name=_('محبوب'),
        default=False,
    )
    is_engaging = models.BooleanField(
        verbose_name=_('جذاب'),
        default=False,
    )
    created = jmodels.jDateTimeField(
    verbose_name=_('تاریخ ایجاد'),
    auto_now_add=True,
    )
    updated = jmodels.jDateTimeField(
        verbose_name=_('تاریخ تغییر'),
        auto_now=True,
    )
    published_date = jmodels.jDateTimeField(
        verbose_name=_('تاریخ انتشار'),
        default=timezone.now,
    )

    objects = models.Manager()
    published = PublishedManager()
    publishings = PublishingManager()
    
    class Meta:
        verbose_name = 'مقاله'
        verbose_name_plural = 'مقاله‌ها'
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['slug']),
        ]

    def get_similar_articles(self):
        return Article.published.prefetch_related('tags').filter(
            models.Q(tags__in=self.tags.all()) |
            models.Q(category_content_type=self.category_content_type,
                     category_object_id=self.category_object_id)
        ).exclude(id=self.id).distinct()[:10]

    def __str__(self):
        return self.title



class Comment(models.Model):
    author_name = models.CharField(
        max_length=256,
        verbose_name=_('نام'),
    )
    author_email = models.CharField(
        max_length=256,
        verbose_name=_('ایمیل'),
    )
    text = models.TextField(
        verbose_name=_('متن'),
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        verbose_name=_('مقاله'),
        related_name='comments',
    )
    is_approved = models.BooleanField(
        verbose_name=_('تایید شده'),
        default=False,
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name=_('پاسخ به'),
        related_name='replies',
        null=True,
        blank=True,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )
    
    objects = models.Manager()
    approved = ApprovedManager()
    
    class Meta:
        verbose_name = 'کامنت'
        verbose_name_plural = 'کامنت‌ها'
        ordering = ['-created']

    def __str__(self):
        return f'{self.author_name} - {self.article}'

    def get_replies(self):
        return self.replies.all()

    def clean(self):
        super().clean()
        if self.reply_to and self.reply_to.article_id != self.article_id:
            raise ValidationError("کامنتی که به آن ریپلای میکنید، متعلق به مقاله جاری نیست.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
