import os
import logging
from datetime import datetime
from jdatetime import datetime as jdatetime
from config import MAX_BACKUPS

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileManager:
    @staticmethod
    def cleanup_old_backups(backup_dir):
        """حذف بکاپ‌های قدیمی‌تر از حد مجاز (MAX_BACKUPS)"""
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                logger.debug(f"Created directory: {backup_dir}")
            
            # فقط فایل‌ها را بررسی کن
            files = [
                f for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and
                (f.endswith(".tar.gz") or f.endswith(".sql"))
            ]
            if len(files) > MAX_BACKUPS and MAX_BACKUPS > 0:  # بررسی صفر بودن MAX_BACKUPS
                # مرتب‌سازی بر اساس زمان ایجاد
                files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                for old_file in files[:-MAX_BACKUPS]:
                    file_path = os.path.join(backup_dir, old_file)
                    os.remove(file_path)
                    logger.debug(f"Removed old backup: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups in {backup_dir}: {e}")

    @staticmethod
    def latest_file(backup_dir, extension):
        """پیدا کردن جدیدترین فایل با پسوند مشخص"""
        try:
            if not os.path.exists(backup_dir):
                logger.error(f"Directory does not exist: {backup_dir}")
                return None
            
            # فقط فایل‌ها را بررسی کن
            files = [
                f for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(extension)
            ]
            if not files:
                logger.error(f"No files with extension {extension} found in {backup_dir}")
                return None
            
            # مرتب‌سازی بر اساس زمان ایجاد فایل
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
            logger.debug(f"Latest file found in {backup_dir}: {latest_file}")
            return latest_file
        except Exception as e:
            logger.error(f"Error finding latest file in {backup_dir}: {e}")
            return None

    @staticmethod
    def get_file_datetime(filename):
        """استخراج تاریخ شمسی از نام فایل"""
        try:
            # فرمت نام فایل: db_1404-06-16-06-13.sql یا media_1404-06-16-06-13.tar.gz
            if '_' not in filename:
                raise ValueError("نام فایل فرمت موردنظر را ندارد")
            date_part = filename.split('_')[1]  # گرفتن 1404-06-16-06-13
            if not date_part:
                raise ValueError("بخش تاریخ در نام فایل خالی است")
            miladi_datetime = datetime.strptime(date_part, "%Y-%m-%d-%H-%M")
            shamsi_datetime = jdatetime.fromgregorian(datetime=miladi_datetime)
            return shamsi_datetime.strftime("%Y-%m-%d %H:%M")  # فرمت شمسی
        except Exception as e:
            logger.error(f"Error parsing date from filename {filename}: {e}")
            return "نامشخص"