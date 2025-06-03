from django.contrib import admin
from .models import BackupLog, BackupRestoreRequest
from .forms import BackupLogAdminForm, BackupRestoreRequestForm


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    form = BackupLogAdminForm
    list_display = ['backup_type', 'app_name', 'model_name', 'created_at']
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {
            'fields': ('backup_type', 'app_name', 'model_name', 'created_at')
        }),
    )


@admin.register(BackupRestoreRequest)
class BackupRestoreRequestAdmin(admin.ModelAdmin):
    form = BackupRestoreRequestForm 
    list_display = [
        'backup_file_link',
        'get_backup_type',
        'get_app_name',
        'get_model_name',
        'requested_at',
        'restored',
    ]
    readonly_fields = ['requested_at', 'restored']

    def backup_file_link(self, obj):
        if obj.backup_file:
            return f'<a href="{obj.backup_file.url}" target="_blank">{obj.backup_file.name}</a>'
        return "-"
    backup_file_link.short_description = "فایل بکاپ"
    backup_file_link.allow_tags = True  # در نسخه‌های جدید Django لازم نیست اما بعضی جاها می‌خواد

    def get_backup_type(self, obj):
        return obj.backup_log.backup_type.upper()
    get_backup_type.short_description = 'نوع بکاپ'

    def get_app_name(self, obj):
        return obj.backup_log.app_name or 'ALL'
    get_app_name.short_description = 'اپلیکیشن'

    def get_model_name(self, obj):
        return obj.backup_log.model_name or 'ALL'
    get_model_name.short_description = 'مدل'
