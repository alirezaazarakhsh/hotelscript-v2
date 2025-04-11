from django.contrib import admin
from .models import (
    StoryCategory,
)
from .forms import (
    StoryCategoryAdminForm,
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
