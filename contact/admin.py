from django.contrib import admin
from .models import (
    ContactMessage,
)

# Register your models here.
@admin.register(ContactMessage)
class RuleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'full_name',
        'phone_number',
        'email',
        'created',
    )
    search_fields = (
        'title',
        'text',
        'full_name',
        'phone_number',
        'email',
    )
    date_hierarchy = 'created'