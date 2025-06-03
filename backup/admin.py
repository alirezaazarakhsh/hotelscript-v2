from django.contrib import admin
from .models import BackupLog, BackupRestoreRequest
from .forms import BackupLogAdminForm

@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    form = BackupLogAdminForm
    list_display = ['backup_type', 'app_name', 'model_name', 'file_path', 'created_at']
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {
            'fields': ('backup_type', 'app_name', 'model_name', 'file_path', 'created_at')
        }),
    )


@admin.register(BackupRestoreRequest)
class BackupRestoreRequestAdmin(admin.ModelAdmin):
    list_display = ['backup_file', 'restore_type', 'app_name', 'model_name', 'requested_at', 'restored']
    readonly_fields = ['requested_at', 'restored']
