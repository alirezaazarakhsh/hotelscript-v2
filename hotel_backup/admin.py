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
    # غیرفعال کردن دسترسی‌های ایجاد، تغییر و حذف رکورد چون مدل صوری است
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
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
        # ریدایرکت خودکار به صفحه داشبورد اختصاصی
        return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def backup_dashboard_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            'title': 'مدیریت بکاپ و بازگردانی هتل‌ها و اتاق‌ها',
        }
        return render(request, 'admin/hotel_backup/dashboard.html', context)

    def download_json(self, request):
        """دانلود اطلاعات متنی دیتابیس به صورت JSON"""
        try:
            json_str = HotelBackupService.export_json_string()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="hotels_data_{now_str}.json"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در ایجاد فایل JSON: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_media(self, request):
        """دانلود تمامی تصاویر و مدیاها به صورت ZIP"""
        try:
            buf = HotelBackupService.export_media_zip()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="hotels_media_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در ساخت فایل فشرده عکس‌ها: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_full(self, request):
        """دانلود پکیج کامل شامل دیتابیس (JSON) و مدیاها در قالب یک فایل ZIP"""
        try:
            buf = HotelBackupService.export_full_backup_zip()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="hotels_full_backup_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در ساخت پکیج کامل بکاپ: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def restore_backup(self, request):
        """بازگردانی اطلاعات از فایل‌های ZIP یا JSON"""
        if request.method == 'POST':
            file = request.FILES.get('backup_file')
            if not file:
                messages.error(request, "لطفاً ابتدا یک فایل بکاپ انتخاب کنید.")
                return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

            filename = file.name.lower()

            if filename.endswith('.zip'):
                success, msg = HotelBackupService.restore_from_zip(file)
            elif filename.endswith('.json'):
                success, msg = HotelBackupService.restore_from_json(file)
            else:
                success, msg = False, "فرمت فایل نامعتبر است! فقط پسوندهای .zip و .json مجاز هستند."

            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)

        return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))