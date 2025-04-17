from django.db import models
from django.db.models import (
    Count,
    Q,
)
from datetime import (
    datetime,
    timedelta,
)

STORY_EXPIRED_AT = datetime.now() - timedelta(days=2)

class HasStoryManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .annotate(active_story_count=Count('stories', filter=Q(stories__created__gt=STORY_EXPIRED_AT)))\
                .filter(active_story_count__gt=0)\
                .order_by('order')

class PublishedManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(status='published_date')\
                .filter(published_date__lte=datetime.now())\
                .order_by('-published_date')

class PopularManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(status='published_date')\
                .filter(is_popular=True)\
                .filter(published_date__lte=datetime.now())\
                .order_by('-published_date')

class EngagingManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(status='published_date')\
                .filter(is_engaging=True)\
                .filter(published_date__lte=datetime.now())\
                .order_by('-published_date')

class PublishingManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(status='published_date')\
                .filter(published_date__gt=datetime.now())\
                .order_by('published_date')
