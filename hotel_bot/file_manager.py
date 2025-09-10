import os
import logging
from datetime import datetime
from jdatetime import datetime as jdatetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileManager:
    @staticmethod
    def list_latest_files(backup_dir, extension, max_files=7):
        """لیست آخرین N فایل با پسوند مشخص"""
        try:
            if not os.path.exists(backup_dir):
                return []

            files = [
                f for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(extension)
            ]
            # مرتب‌سازی بر اساس زمان ایجاد (جدیدترین اول)
            files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)), reverse=True)
            return files[:max_files]
        except Exception as e:
            logger.error(f"Error listing latest files in {backup_dir}: {e}")
            return []

    @staticmethod
    def latest_file(backup_dir, extension):
        """پیدا کردن جدیدترین فایل"""
        try:
            files = FileManager.list_latest_files(backup_dir, extension, max_files=1)
            return files[0] if files else None
        except Exception as e:
            logger.error(f"Error getting latest file in {backup_dir}: {e}")
            return None

    @staticmethod
    def cleanup_old_backups(backup_dir, max_files=10):
        """پاکسازی بکاپ‌های قدیمی (بیش از حد مجاز)"""
        try:
            if not os.path.exists(backup_dir):
                return
            
            files = [f for f in os.listdir(backup_dir) if os.path.isfile(os.path.join(backup_dir, f))]
            
            if len(files) > max_files:
                # مرتب‌سازی بر اساس زمان ایجاد (قدیمی‌ترین اول)
                files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                
                # حذف فایل‌های اضافی
                for old_file in files[:-max_files]:
                    os.remove(os.path.join(backup_dir, old_file))
                    logger.info(f"Removed old backup: {old_file}")
        except Exception as e:
            logger.error(f"Error cleaning backups in {backup_dir}: {e}")

    @staticmethod
    def get_file_datetime(filename):
        """استخراج تاریخ از نام فایل"""
        try:
            if '_' not in filename:
                return "نامشخص"
            
            # استخراج قسمت تاریخ از نام فایل
            date_part = filename.split('_')[1].split('.')[0]
            dt = datetime.strptime(date_part, "%Y-%m-%d-%H-%M")
            
            # تبدیل به تاریخ شمسی
            shamsi_dt = jdatetime.fromgregorian(datetime=dt)
            return shamsi_dt.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.warning(f"Error parsing date from filename {filename}: {e}")
            return "نامشخص"

    @staticmethod
    def get_file_size(file_path):
        """محاسبه حجم فایل به مگابایت"""
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return "نامشخص"