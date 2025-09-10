import os
import logging
from datetime import datetime
from jdatetime import datetime as jdatetime
from hotel_bot.config import MAX_BACKUPS

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileManager:
    @staticmethod
    def cleanup_old_backups(backup_dir, max_files=MAX_BACKUPS):
        """حذف بکاپ‌های قدیمی‌تر از حد مجاز"""
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

            if len(files) > max_files and max_files > 0:
                # مرتب‌سازی بر اساس زمان ایجاد
                files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                for old_file in files[:-max_files]:
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

            files = [
                f for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(extension)
            ]
            if not files:
                return None

            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
            logger.debug(f"Latest file found in {backup_dir}: {latest_file}")
            return latest_file
        except Exception as e:
            logger.error(f"Error finding latest file in {backup_dir}: {e}")
            return None

    @staticmethod
    def list_latest_files(backup_dir, extension, max_files=MAX_BACKUPS):
        """لیست آخرین N فایل با پسوند مشخص"""
        try:
            if not os.path.exists(backup_dir):
                return []

            files = [
                f for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(extension)
            ]
            files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)), reverse=True)
            return files[:max_files]
        except Exception as e:
            logger.error(f"Error listing latest files in {backup_dir}: {e}")
            return []

@staticmethod
def get_file_datetime(filename):
    """استخراج تاریخ شمسی از نام فایل"""
    try:
        # فرمت نام فایل: db_1404-06-16-06-13.sql یا media_1404-06-16-06-13.tar.gz
        if '_' not in filename:
            logger.warning(f"Invalid filename format (no underscore): {filename}")
            return "نامشخص"
        date_part = filename.split('_')[1].split('.')[0]  # گرفتن 1404-06-16-06-13
        miladi_datetime = datetime.strptime(date_part, "%Y-%m-%d-%H-%M")
        shamsi_datetime = jdatetime.fromgregorian(datetime=miladi_datetime)
        formatted_date = shamsi_datetime.strftime("%Y-%m-%d %H:%M")
        logger.debug(f"Parsed datetime for {filename}: {formatted_date}")
        return formatted_date
    except Exception as e:
        logger.warning(f"Error parsing date from filename {filename}: {str(e)}")
        return "نامشخص"