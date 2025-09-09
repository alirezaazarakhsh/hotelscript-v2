import os
import subprocess
import asyncio
import logging
from datetime import datetime
import pytz
from jdatetime import datetime as jdatetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from hotel_bot.config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from hotel_bot.file_manager import FileManager
from hotel_bot.menu_manager import MenuManager

# تنظیم لاگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تنظیم منطقه زمانی تهران
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

MAX_BACKUPS = 7  # حداکثر تعداد بکاپ‌های ذخیره شده

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال بکاپ‌گیری دیتابیس...")
        os.makedirs(DB_BACKUP_DIR, exist_ok=True)

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} db {timestamp['file']}", shell=True, capture_output=True, text=True)
        logger.debug(f"DB backup stdout: {result.stdout}\nstderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ دیتابیس: {result.stderr}")
            await MenuManager.show_main_menu(user_id, context)
            return

        # پیدا کردن آخرین فایل
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        if db_file:
            file_path = os.path.join(DB_BACKUP_DIR, db_file)
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"),
                                            caption=f"فایل بکاپ دیتابیس\nFile: {db_file}\n{timestamp['display']}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ دیتابیس پیدا نشد!")

        # پاکسازی قدیمی‌ها
        FileManager.cleanup_old_backups(DB_BACKUP_DIR, max_files=MAX_BACKUPS)
        await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال بکاپ‌گیری مدیا...")
        os.makedirs(MEDIA_BACKUP_DIR, exist_ok=True)

        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} media {timestamp['file']}", shell=True, capture_output=True, text=True)
        logger.debug(f"Media backup stdout: {result.stdout}\nstderr: {result.stderr}")

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "خطای ناشناخته"
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ مدیا: {error_msg}")
            await MenuManager.show_main_menu(user_id, context)
            return

        media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        if media_file:
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"✅ بکاپ مدیا آماده شد.\n💾 لینک دانلود: {media_url}\n{timestamp['display']}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ مدیا پیدا نشد!")

        # پاکسازی قدیمی‌ها
        FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR, max_files=MAX_BACKUPS)
        await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def list_backups(user_id, context):
        # دکمه برای آخرین ۷ بکاپ دیتابیس
        db_files = FileManager.list_latest_files(DB_BACKUP_DIR, extension=".sql", max_files=MAX_BACKUPS)
        media_files = FileManager.list_latest_files(MEDIA_BACKUP_DIR, extension=".tar.gz", max_files=MAX_BACKUPS)

        keyboard = []
        if db_files:
            keyboard.append([InlineKeyboardButton("📁 بکاپ دیتابیس", callback_data="none")])
            for f in db_files:
                path = os.path.join(DB_BACKUP_DIR, f)
                keyboard.append([InlineKeyboardButton(f"📄 {f}", callback_data=f"db::{path}")])
        if media_files:
            keyboard.append([InlineKeyboardButton("📁 بکاپ مدیا", callback_data="none")])
            for f in media_files:
                url = MEDIA_BASE_URL + f
                keyboard.append([InlineKeyboardButton(f"📄 {f}", url=url)])

        if not keyboard:
            await context.bot.send_message(chat_id=user_id, text="❌ بکاپی موجود نیست!")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text="📦 آخرین بکاپ‌ها:", reply_markup=reply_markup)

    @staticmethod
    def get_timestamp():
        now = datetime.now(TEHRAN_TZ)
        shamsi = jdatetime.fromgregorian(datetime=now, locale='fa_IR')
        return {
            "display": shamsi.strftime("%Y-%m-%d - %H:%M"),
            "file": shamsi.strftime("%Y-%m-%d-%H-%M")
        }
