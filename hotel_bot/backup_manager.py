import os
import subprocess
import logging
import shutil
from datetime import datetime, timedelta
import pytz
from jdatetime import datetime as jdatetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from hotel_bot.config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from hotel_bot.file_manager import FileManager
from hotel_bot.menu_manager import MenuManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

class BackupManager:
    DAILY_LIMIT = 2
    WEEKLY_LIMIT = 10
    MAX_LIST = 7

    @staticmethod
    def user_backup_dir(user_id, backup_type):
        if backup_type == "db":
            return os.path.join(DB_BACKUP_DIR, str(user_id))
        elif backup_type == "media":
            return os.path.join(MEDIA_BACKUP_DIR, str(user_id))
        return None

    @staticmethod
    def get_timestamp():
        now = datetime.now(TEHRAN_TZ)
        shamsi = jdatetime.fromgregorian(datetime=now, locale='fa_IR')
        return {
            "display": shamsi.strftime("%Y-%m-%d - %H:%M"),
            "file": shamsi.strftime("%Y-%m-%d-%H-%M")
        }

    @staticmethod
    def get_backup_count_today(user_id, backup_type):
        """تعداد بکاپ‌های امروز کاربر"""
        dir_path = BackupManager.user_backup_dir(user_id, backup_type)
        if not os.path.exists(dir_path):
            return 0
        
        today = datetime.now().strftime("%Y-%m-%d")
        files = [f for f in os.listdir(dir_path) 
                if os.path.isfile(os.path.join(dir_path, f)) and today in f]
        return len(files)

    @staticmethod
    def cleanup_old_weekly_backups():
        """پاکسازی بکاپ‌های هفته‌های قبل"""
        try:
            for backup_type in ["db", "media"]:
                base_dir = DB_BACKUP_DIR if backup_type == "db" else MEDIA_BACKUP_DIR
                
                if not os.path.exists(base_dir):
                    continue
                
                # پیدا کردن اولین روز هفته جاری
                today = datetime.now()
                start_of_week = today - timedelta(days=today.weekday())
                
                for user_dir in os.listdir(base_dir):
                    user_path = os.path.join(base_dir, user_dir)
                    if not os.path.isdir(user_path):
                        continue
                    
                    for file_name in os.listdir(user_path):
                        file_path = os.path.join(user_path, file_name)
                        if os.path.isfile(file_path):
                            # استخراج تاریخ از نام فایل
                            try:
                                date_str = file_name.split('_')[1].split('.')[0]
                                file_date = datetime.strptime(date_str, "%Y-%m-%d-%H-%M")
                                
                                # اگر فایل از هفته قبل است، حذف شود
                                if file_date < start_of_week:
                                    os.remove(file_path)
                                    logger.info(f"Removed old weekly backup: {file_path}")
                            except (IndexError, ValueError):
                                continue
        except Exception as e:
            logger.error(f"Error in weekly cleanup: {e}")

    @staticmethod
    async def monthly_auto_backup():
        """بکاپ ماهانه اتوماتیک"""
        try:
            timestamp = BackupManager.get_timestamp()
            
            # بکاپ دیتابیس
            db_backup_script = os.path.join(PROJECT_DIR, "backup.sh")
            result = subprocess.run(f"{db_backup_script} db auto_{timestamp['file']} system", 
                                  shell=True, capture_output=True, text=True)
            logger.info(f"Monthly DB backup result: {result.stdout}")
            
            # بکاپ مدیا
            media_backup_script = os.path.join(PROJECT_DIR, "backup.sh")
            result = subprocess.run(f"{media_backup_script} media auto_{timestamp['file']} system", 
                                  shell=True, capture_output=True, text=True)
            logger.info(f"Monthly media backup result: {result.stdout}")
            
        except Exception as e:
            logger.error(f"Error in monthly auto backup: {e}")

    # ---------------- بکاپ دیتابیس ----------------
    @staticmethod
    async def backup_database(user_id, context):
        # بررسی محدودیت روزانه
        if BackupManager.get_backup_count_today(user_id, "db") >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ دیتابیس رسیدید!")
            return

        dir_path = BackupManager.user_backup_dir(user_id, "db")
        os.makedirs(dir_path, exist_ok=True)

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        
        result = subprocess.run(f"{backup_script} db {timestamp['file']} {user_id}", 
                              shell=True, capture_output=True, text=True)
        logger.debug(result.stdout)
        logger.debug(result.stderr)

        db_file = FileManager.latest_file(dir_path, ".sql")
        if db_file:
            await context.bot.send_document(chat_id=user_id,
                                          document=open(os.path.join(dir_path, db_file), "rb"),
                                          caption=f"📦 بکاپ دیتابیس\n{timestamp['display']}")
        
        FileManager.cleanup_old_backups(dir_path, max_files=BackupManager.WEEKLY_LIMIT)
        await MenuManager.show_main_menu(user_id, context)

    # ---------------- بکاپ مدیا ----------------
    @staticmethod
    async def backup_media(user_id, context):
        # بررسی محدودیت روزانه
        if BackupManager.get_backup_count_today(user_id, "media") >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ مدیا رسیدید!")
            return

        dir_path = BackupManager.user_backup_dir(user_id, "media")
        os.makedirs(dir_path, exist_ok=True)

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        
        result = subprocess.run(f"{backup_script} media {timestamp['file']} {user_id}", 
                              shell=True, capture_output=True, text=True)
        logger.debug(result.stdout)
        logger.debug(result.stderr)

        media_file = FileManager.latest_file(dir_path, ".tar.gz")
        if media_file:
            url = f"{MEDIA_BASE_URL}{user_id}/{media_file}"
            await context.bot.send_message(chat_id=user_id, text=f"📦 بکاپ مدیا آماده شد.\n💾 لینک: {url}")
        
        FileManager.cleanup_old_backups(dir_path, max_files=BackupManager.WEEKLY_LIMIT)
        await MenuManager.show_main_menu(user_id, context)

    # ---------------- لیست بکاپ ----------------
    @staticmethod
    async def list_backups(user_id, context, backup_type=None):
        """نمایش لیست بکاپ‌ها با امکان فیلتر بر اساس نوع"""
        keyboard = [
            [
                InlineKeyboardButton("📁 بکاپ دیتابیس", callback_data="list_db_backups"),
                InlineKeyboardButton("📁 بکاپ مدیا", callback_data="list_media_backups")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="backup_menu")]
        ]
        
        if not backup_type:
            await context.bot.send_message(
                chat_id=user_id, 
                text="📦 لطفا نوع بکاپ مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        if backup_type == "db":
            await BackupManager._list_db_backups(user_id, context)
        elif backup_type == "media":
            await BackupManager._list_media_backups(user_id, context)

    @staticmethod
    async def _list_db_backups(user_id, context):
        """لیست بکاپ‌های دیتابیس"""
        dir_path = BackupManager.user_backup_dir(user_id, "db")
        db_files = FileManager.list_latest_files(dir_path, ".sql", BackupManager.MAX_LIST)
        
        if not db_files:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ بکاپ دیتابیسی موجود نیست!")
            return
        
        keyboard = []
        for idx, file_name in enumerate(db_files, 1):
            file_path = os.path.join(dir_path, file_name)
            keyboard.append([
                InlineKeyboardButton(f"{idx}. {file_name}", callback_data=f"send_db::{file_path}"),
                InlineKeyboardButton("🗑️", callback_data=f"delete_db::{file_path}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id, 
            text="📦 آخرین بکاپ‌های دیتابیس:",
            reply_markup=reply_markup
        )

    @staticmethod
    async def _list_media_backups(user_id, context):
        """لیست بکاپ‌های مدیا"""
        dir_path = BackupManager.user_backup_dir(user_id, "media")
        media_files = FileManager.list_latest_files(dir_path, ".tar.gz", BackupManager.MAX_LIST)
        
        if not media_files:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ بکاپ مدیایی موجود نیست!")
            return
        
        keyboard = []
        for idx, file_name in enumerate(media_files, 1):
            url = f"{MEDIA_BASE_URL}{user_id}/{file_name}"
            keyboard.append([
                InlineKeyboardButton(f"{idx}. {file_name}", url=url),
                InlineKeyboardButton("🗑️", callback_data=f"delete_media::{os.path.join(dir_path, file_name)}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id, 
            text="📦 آخرین بکاپ‌های مدیا:",
            reply_markup=reply_markup
        )

    # ---------------- ارسال مجدد بکاپ ----------------
    @staticmethod
    async def send_backup_file(user_id, context, file_path, backup_type):
        """ارسال مجدد فایل بکاپ"""
        try:
            if backup_type == "db" and os.path.exists(file_path):
                await context.bot.send_document(
                    chat_id=user_id,
                    document=open(file_path, "rb"),
                    caption=f"📦 بکاپ دیتابیس\n{os.path.basename(file_path)}"
                )
            elif backup_type == "media" and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                url = f"{MEDIA_BASE_URL}{user_id}/{file_name}"
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"📦 بکاپ مدیا\n💾 لینک: {url}"
                )
            else:
                await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ یافت نشد!")
        except Exception as e:
            logger.error(f"Error sending backup file: {e}")
            await context.bot.send_message(chat_id=user_id, text="❌ خطا در ارسال فایل بکاپ!")

    # ---------------- حذف بکاپ ----------------
    @staticmethod
    async def delete_backup(user_id, context, file_path):
        """حذف فایل بکاپ"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                await context.bot.send_message(chat_id=user_id, text="✅ بکاپ با موفقیت حذف شد!")
                
                # به‌روزرسانی لیست
                backup_type = "db" if file_path.endswith(".sql") else "media"
                if backup_type == "db":
                    await BackupManager._list_db_backups(user_id, context)
                else:
                    await BackupManager._list_media_backups(user_id, context)
            else:
                await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ یافت نشد!")
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            await context.bot.send_message(chat_id=user_id, text="❌ خطا در حذف بکاپ!")