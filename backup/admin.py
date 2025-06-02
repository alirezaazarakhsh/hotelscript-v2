# backup/admin.py
from django.contrib import admin
from .models import AppModule, Backup

@admin.register(AppModule)
class AppModuleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'verbose_name',
    )
    search_fields = (
        'name',
        'verbose_name',
    )
    ordering = ('name',)


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'app',
        'is_full_backup',
        'file',
        'created_at',
        'restored',
    )
    list_filter = (
        'is_full_backup',
        'restored',
        'created_at',
    )
    search_fields = (
        'app__name',
        'file',
    )
    ordering = ('-created_at',)
