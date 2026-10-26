# hotel_backup/admin.py
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from .models import HotelBackupManager
from .services import HotelBackupService

@admin.register(HotelBackupManager)
class HotelBackupManagerAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.backup_dashboard_view), name='hotel_backup_dashboard'),
            path('download-json/', self.admin_site.admin_view(self.download_json), name='hotel_backup_download_json'),
            path('download-media/', self.admin_site.admin_view(self.download_media), name='hotel_backup_download_media'),
            path('download-full/', self.admin_site.admin_view(self.download_full), name='hotel_backup_download_full'),
            path('restore/', self.admin_site.admin_view(self.restore_backup), name='hotel_backup_restore'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        # ریدایرکت مستقیم به داشبورد اختصاصی بکاپ
        return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def backup_dashboard_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            'title': 'مدیریت بکاپ و بازگردانی هتل‌ها و اتاق‌ها',
        }
        return render(request, 'admin/hotel_backup/dashboard.html', context)

    def download_json(self, request):
        buf = HotelBackupService.export_json()
        now_str = timezone.now().strftime('%Y%m%d_%H%M')
        response = HttpResponse(buf.getvalue(), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="hotels_data_{now_str}.json"'
        return response

    def download_media(self, request):
        buf = HotelBackupService.export_media_zip()
        now_str = timezone.now().strftime('%Y%m%d_%H%M')
        response = HttpResponse(buf.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="hotels_media_{now_str}.zip"'
        return response

    def download_full(self, request):
        buf = HotelBackupService.export_full_backup_zip()
        now_str = timezone.now().strftime('%Y%m%d_%H%M')
        response = HttpResponse(buf.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="hotels_full_backup_{now_str}.zip"'
        return response

    def restore_backup(self, request):
        if request.method == 'POST' and request.FILES.get('backup_file'):
            file = request.FILES['backup_file']
            filename = file.name.lower()

            if filename.endswith('.zip'):
                success, msg = HotelBackupService.restore_from_zip(file)
            elif filename.endswith('.json'):
                success, msg = HotelBackupService.restore_from_json(file)
            else:
                success, msg = False, "فقط فرمت‌های zip و json مجاز هستند."

            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)

        return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))