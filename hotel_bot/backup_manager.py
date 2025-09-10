import os
import subprocess
import logging
from datetime import datetime
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

    # ---------------- بکاپ دیتابیس ----------------
    @staticmethod
    async def backup_database(user_id, context):
        dir_path = BackupManager.user_backup_dir(user_id, "db")
        os.makedirs(dir_path, exist_ok=True)

        # محدودیت روزانه
        today_files = [f for f in FileManager.list_latest_files(dir_path, ".sql", 100)
                       if datetime.now().strftime("%Y-%m-%d") in f]
        if len(today_files) >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ دیتابیس رسیدید!")
            return

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} db {timestamp['file']} {user_id}", shell=True, capture_output=True, text=True)
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
        dir_path = BackupManager.user_backup_dir(user_id, "media")
        os.makedirs(dir_path, exist_ok=True)

        today_files = [f for f in FileManager.list_latest_files(dir_path, ".tar.gz", 100)
                       if datetime.now().strftime("%Y-%m-%d") in f]
        if len(today_files) >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ مدیا رسیدید!")
            return

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} media {timestamp['file']} {user_id}", shell=True, capture_output=True, text=True)
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
    async def list_backups(user_id, context):
        db_dir = BackupManager.user_backup_dir(user_id, "db")
        media_dir = BackupManager.user_backup_dir(user_id, "media")

        db_files = FileManager.list_latest_files(db_dir, ".sql", BackupManager.MAX_LIST)
        media_files = FileManager.list_latest_files(media_dir, ".tar.gz", BackupManager.MAX_LIST)

        keyboard = []

        # دکمه دیتابیس
        if db_files:
            keyboard.append([InlineKeyboardButton("📁 بکاپ دیتابیس", callback_data="none")])
            for idx, f in enumerate(db_files, 1):
                path = os.path.join(db_dir, f)
                keyboard.append([InlineKeyboardButton(f"{idx}. {f}", callback_data=f"db::{path}")])

        # دکمه مدیا
        if media_files:
            keyboard.append([InlineKeyboardButton("📁 بکاپ مدیا", callback_data="none")])
            for idx, f in enumerate(media_files, 1):
                url = f"{MEDIA_BASE_URL}{user_id}/{f}"
                keyboard.append([InlineKeyboardButton(f"{idx}. {f}", url=url)])

        if not keyboard:
            await context.bot.send_message(chat_id=user_id, text="❌ بکاپی موجود نیست!")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text="📦 آخرین بکاپ‌ها:", reply_markup=reply_markup)
