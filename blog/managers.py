from django.db import models
from django.db.models import (
    Count,
    Q,
)
from django.utils import timezone
from datetime import (
    timedelta,
)

STORY_EXPIRED_AT = timezone.now() - timedelta(days=2)

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
                .filter(status='published')\
                .filter(published_date__lte=timezone.now())\
                .order_by('-published_date')

class PublishingManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(status='published')\
                .filter(published_date__gt=timezone.now())\
                .order_by('published_date')

class ApprovedManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .filter(is_approved=True)\
                .order_by('-created')
