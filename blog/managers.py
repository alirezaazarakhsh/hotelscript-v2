from django.db import models
from django.db.models import (
    Count,
    Q
)
from datetime import datetime, timedelta

STORY_EXPIRED_AT = datetime.now() - timedelta(days=2)

class HasStoryManager(models.Manager):
    def get_queryset(self):
        return super()\
                .get_queryset()\
                .annotate(active_story_count=Count('stories', filter=Q(stories__created__gt=STORY_EXPIRED_AT)))\
                .filter(active_story_count__gt=0)\
                .order_by('order')