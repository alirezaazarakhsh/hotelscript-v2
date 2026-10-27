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

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.backup_dashboard_view), name='hotel_backup_dashboard'),
            
            # دانلودهای سراسری (کل سیستم)
            path('download/all/full/', self.admin_site.admin_view(self.download_all_full), name='hotel_backup_all_full'),
            path('download/all/json/', self.admin_site.admin_view(self.download_all_json), name='hotel_backup_all_json'),
            path('download/all/media/', self.admin_site.admin_view(self.download_all_media), name='hotel_backup_all_media'),
            
            # دانلودهای دسته‌بندی‌شده (یک بخش خاص)
            path('download/section/<str:section>/full/', self.admin_site.admin_view(self.download_section_full), name='hotel_backup_section_full'),
            path('download/section/<str:section>/json/', self.admin_site.admin_view(self.download_section_json), name='hotel_backup_section_json'),
            path('download/section/<str:section>/media/', self.admin_site.admin_view(self.download_section_media), name='hotel_backup_section_media'),
            
            # دانلود جداگانه یک پوشه خاص از مدیا (استفاده از path جهت پشتیبانی از اسلش‌ها مثل images/config)
            path('download/folder/<path:folder_name>/', self.admin_site.admin_view(self.download_single_folder), name='hotel_backup_single_folder'),
            
            # بازگردانی
            path('restore/', self.admin_site.admin_view(self.restore_backup), name='hotel_backup_restore'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def backup_dashboard_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            'title': 'مرکز جامع بکاپ و بازگردانی تفکیک‌شده سیستم',
            'sections': HotelBackupService.SECTIONS,
        }
        return render(request, 'admin/hotel_backup/dashboard.html', context)

    # --- اکشن‌های دانلود سراسری ---
    def download_all_full(self, request):
        try:
            buf = HotelBackupService.export_full_backup_zip()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="system_full_backup_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در ایجاد بکاپ کامل: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_all_json(self, request):
        try:
            json_str = HotelBackupService.export_json_string()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="system_all_data_{now_str}.json"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در استخراج JSON کل سیستم: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_all_media(self, request):
        try:
            buf = HotelBackupService.export_media_zip()
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="system_all_media_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در زیپ مدیا: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    # --- اکشن‌های دانلود بر اساس دسته‌بندی ---
    def download_section_full(self, request, section):
        try:
            buf = HotelBackupService.export_full_backup_zip(section)
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{section}_full_package_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در دانلود پکیج {section}: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_section_json(self, request, section):
        try:
            sec_info = HotelBackupService.SECTIONS.get(section, {})
            json_str = HotelBackupService.export_json_string(sec_info.get('models', []))
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{section}_data_{now_str}.json"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در دانلود JSON بخش {section}: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    def download_section_media(self, request, section):
        try:
            sec_info = HotelBackupService.SECTIONS.get(section, {})
            buf = HotelBackupService.export_media_zip(sec_info.get('media', []))
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{section}_media_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در دانلود مدیای بخش {section}: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    # --- اکشن دانلود تفکیک‌شده تک‌پوشه‌ای ---
    def download_single_folder(self, request, folder_name):
        try:
            # امنیت مسیر: جلوگیری از خروج از دایرکتوری مجاز
            if '..' in folder_name:
                messages.error(request, "مسیر غیرمجاز است.")
                return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

            buf = HotelBackupService.export_media_zip([folder_name])
            clean_name = folder_name.replace('/', '_')
            now_str = timezone.now().strftime('%Y%m%d_%H%M')
            response = HttpResponse(buf.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="folder_{clean_name}_{now_str}.zip"'
            return response
        except Exception as e:
            messages.error(request, f"خطا در دانلود پوشه {folder_name}: {str(e)}")
            return HttpResponseRedirect(reverse('admin:hotel_backup_dashboard'))

    # --- اکشن بازگردانی (ریستور) ---
    def restore_backup(self, request):
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