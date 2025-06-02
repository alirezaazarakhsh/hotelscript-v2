from django.contrib import admin
from .models import AppModule, AppModel, Backup

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


@admin.register(AppModel)
class AppModelAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'verbose_name',
        'app',
    )
    search_fields = (
        'name',
        'verbose_name',
        'app__name',
    )
    list_filter = (
        'app',
    )
    ordering = ('app', 'name')


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'app',
        'app_model',
        'is_full_backup',
        'file',
        'created_at',
        'restored',
    )
    list_filter = (
        'is_full_backup',
        'restored',
        'created_at',
        'app',
    )
    search_fields = (
        'app__name',
        'app_model__name',
        'file',
    )
    ordering = ('-created_at',)
