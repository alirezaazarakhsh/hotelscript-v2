from django.contrib import admin
from .models import (
    StoryCategory,
    Story,
)
from .forms import (
    StoryCategoryAdminForm,
    StoryAdminForm,
)
# Register your models here.
@admin.register(StoryCategory)
class StoryCategoryAdmin(admin.ModelAdmin):
    form = StoryCategoryAdminForm
    list_display = (
        'id',
        'title',
        'order',
    )
    search_fields = (
        'title',
    )

@admin.register(Story)
class StoryCategoryAdmin(admin.ModelAdmin):
    form = StoryAdminForm
    list_display = (
        'id',
        'category',
    )
    list_filter = (
        'category',
    )
