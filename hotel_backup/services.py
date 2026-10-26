# hotel_backup/services.py
import os
import shutil
import zipfile
import tempfile
from io import BytesIO
from django.conf import settings
from django.core.management import call_command
from django.db import transaction

# نام اپلیکیشن اصلی هتل‌ها (در صورت تفاوت، تغییر دهید)
APP_NAME = 'reservation' 

# مدل‌ها دقیقاً بر اساس اولویت وابستگی (اول پدرها، بعد فرزندها):
BACKUP_MODELS = [
    # ۱. ابتدا آیکون‌ها (پایه کل سیستم)
    'icons.IconShortcut',
    
    # ۲. سطوح کاربری (وابسته به آیکون)
    'config.UserLevel',
    
    # ۳. تعاریف پایه هتل‌ها و شهرها
    f'{APP_NAME}.Province',
    f'{APP_NAME}.City',
    f'{APP_NAME}.HotelType',
    f'{APP_NAME}.HotelTag',
    f'{APP_NAME}.HotelTagPublic',
    f'{APP_NAME}.Facilities',          # وابسته به IconShortcut
    f'{APP_NAME}.RoomFacilities',      # وابسته به IconShortcut
    f'{APP_NAME}.BestHotels',
    
    # ۴. هتل و متعلقات آن
    f'{APP_NAME}.Hotel',
    f'{APP_NAME}.SEOMeta',
    f'{APP_NAME}.HotelGallery',
    f'{APP_NAME}.HotelGalleryImage',
    f'{APP_NAME}.NearbyPlace',
    f'{APP_NAME}.HotelFAQ',            # وابسته به IconShortcut
    f'{APP_NAME}.CancellationPenalty',
    
    # ۵. اتاق‌ها، خدمات و قیمت‌گذاری‌ها
    f'{APP_NAME}.RoomService',
    f'{APP_NAME}.Room',
    f'{APP_NAME}.RoomDatePrice',       # وابسته به UserLevel
    f'{APP_NAME}.ClosedDate',          # وابسته به UserLevel و RoomDatePrice
]

# تمام پوشه‌های مدیای مربوطه (پوشه آیکون‌های SVG اضافه شد)
MEDIA_SUBDIRS = [
    'icons/svg_icons',        # آیکون‌های SVG مدل IconShortcut
    'images/hotels',          # تصاویر هتل‌ها
    'room_images',            # تصاویر اتاق‌ها
    'hotel_gallery',          # گالری تصاویر هتل‌ها
    'images/nearby-places',   # عکس اماکن اطراف
    'images/best_hotels',     # لوگوی هتل‌ها
    'cities',                 # عکس شهرها
]

class HotelBackupService:

    @classmethod
    def export_json(cls) -> BytesIO:
        """خروجی ساختار دیتابیس به صورت JSON استاندارد"""
        buf = BytesIO()
        call_command(
            'dumpdata',
            *BACKUP_MODELS,
            format='json',
            indent=2,
            stdout=buf
        )
        buf.seek(0)
        return buf

    @classmethod
    def export_media_zip(cls) -> BytesIO:
        """فشرده‌سازی و دانلود کل پوشه عکس‌ها و آیکون‌ها به صورت ZIP"""
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for subdir in MEDIA_SUBDIRS:
                folder_path = os.path.join(media_root, subdir)
                if os.path.exists(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, media_root)
                            zf.write(full_path, arcname=rel_path)

        zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def export_full_backup_zip(cls) -> BytesIO:
        """
        پکیج کامل و مستقل:
        شامل فایل data.json (شامل آیکون‌ها، سطوح کاربری، هتل‌ها و اتاق‌ها)
        + پوشه کامل تمام مدیاها و SVGها
        """
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT

        # استخراج دیتای دیتابیس
        json_buffer = cls.export_json()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # ۱. ذخیره فایل JSON در ریشه فایل ZIP
            zf.writestr('data.json', json_buffer.getvalue())

            # ۲. ذخیره فایل‌های تصویری در پوشه media داخل ZIP
            for subdir in MEDIA_SUBDIRS:
                folder_path = os.path.join(media_root, subdir)
                if os.path.exists(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, media_root)
                            archive_path = os.path.join('media', rel_path)
                            zf.write(full_path, arcname=archive_path)

        zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def restore_from_zip(cls, uploaded_file) -> tuple[bool, str]:
        """
        بازگردانی همه‌چیز در دیتابیس جدید:
        1. تصاویر و SVGها به MEDIA_ROOT منتقل می‌شوند
        2. دیتابیس از طریق loaddata لود می‌شود
        """
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(uploaded_file, 'r') as zf:
                zf.extractall(temp_dir)

            # ۱. انتقال فایل‌های مدیا
            extracted_media_dir = os.path.join(temp_dir, 'media')
            media_root = settings.MEDIA_ROOT

            if os.path.exists(extracted_media_dir):
                for root, _, files in os.walk(extracted_media_dir):
                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, extracted_media_dir)
                        dest_file = os.path.join(media_root, rel_path)

                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)

            # ۲. لود داده‌های JSON به دیتابیس
            json_file_path = os.path.join(temp_dir, 'data.json')
            if not os.path.exists(json_file_path):
                return False, "فایل data.json در فایل ZIP یافت نشد!"

            with transaction.atomic():
                call_command('loaddata', json_file_path)

            return True, "اطلاعات (آیکون‌ها، سطوح کاربری، هتل‌ها و اتاق‌ها) به همراه تمامی فایل‌های مدیا با موفقیت بازگردانی شدند."

        except Exception as e:
            return False, f"خطا در بازگردانی: {str(e)}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def restore_from_json(cls, uploaded_file) -> tuple[bool, str]:
        """بازگردانی فقط فایل JSON"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        try:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.close()

            with transaction.atomic():
                call_command('loaddata', temp_file.name)

            return True, "داده‌های JSON با موفقیت در دیتابیس ثبت شدند."
        except Exception as e:
            return False, f"خطا در تزریق JSON: {str(e)}"
        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)