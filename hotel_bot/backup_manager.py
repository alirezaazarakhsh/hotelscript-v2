import os
import subprocess
import logging
from datetime import datetime, timedelta
import pytz
from jdatetime import datetime as jdatetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from hotel_bot.config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL, SUPER_ADMINS
from hotel_bot.file_manager import FileManager
from hotel_bot.menu_manager import MenuManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

class BackupManager:
    DAILY_LIMIT = 2
    WEEKLY_LIMIT = 7
    MAX_LIST = 7

    @staticmethod
    def is_super_admin(user_id):
        return user_id in SUPER_ADMINS

    @staticmethod
    def user_backup_dir(user_id, backup_type):
        user_id_str = str(user_id) if user_id != "system" else "system"
        if backup_type == "db":
            return os.path.join(DB_BACKUP_DIR, user_id_str)
        elif backup_type == "media":
            return os.path.join(MEDIA_BACKUP_DIR, user_id_str)
        return None

    @staticmethod
    def get_timestamp():
        now = datetime.now(TEHRAN_TZ)
        shamsi = jdatetime.fromgregorian(datetime=now, locale='fa_IR')
        return {"display": shamsi.strftime("%Y-%m-%d - %H:%M"), "file": shamsi.strftime("%Y-%m-%d-%H-%M")}

    @staticmethod
    def get_backup_count_today(user_id, backup_type):
        dir_path = BackupManager.user_backup_dir(user_id, backup_type)
        if not os.path.exists(dir_path):
            return 0
        today = datetime.now().strftime("%Y-%m-%d")
        files = [f for f in os.listdir(dir_path) 
                 if os.path.isfile(os.path.join(dir_path, f)) and today in f]
        return len(files)

    @staticmethod
    async def backup_database(user_id, context):
        logger.debug(f"Starting database backup for user {user_id}")
        if not BackupManager.is_super_admin(user_id) and BackupManager.get_backup_count_today(user_id, "db") >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ دیتابیس رسیدید!")
            return

        dir_path = BackupManager.user_backup_dir(user_id, "db")
        os.makedirs(dir_path, exist_ok=True)
        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} db {timestamp['file']} {user_id}", 
                                shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Database backup failed: {result.stderr}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ‌گیری دیتابیس: {result.stderr}")
            return
        db_file = FileManager.latest_file(dir_path, ".sql")
        if db_file:
            await context.bot.send_document(chat_id=user_id,
                                          document=open(os.path.join(dir_path, db_file), "rb"),
                                          caption=f"📦 بکاپ دیتابیس\n{timestamp['display']}")
        # نمایش لیست بکاپ‌ها به جای منوی اصلی
        await BackupManager.list_backups(user_id, context, backup_type="db")

    @staticmethod
    async def backup_media(user_id, context):
        logger.debug(f"Starting media backup for user {user_id}")
        if not BackupManager.is_super_admin(user_id) and BackupManager.get_backup_count_today(user_id, "media") >= BackupManager.DAILY_LIMIT:
            await context.bot.send_message(chat_id=user_id, text="❌ شما امروز به حد مجاز بکاپ مدیا رسیدید!")
            return

        dir_path = BackupManager.user_backup_dir(user_id, "media")
        os.makedirs(dir_path, exist_ok=True)
        timestamp = BackupManager.get_timestamp()
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} media {timestamp['file']} {user_id}", 
                                shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Media backup failed: {result.stderr}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ‌گیری مدیا: {result.stderr}")
            return
        media_file = FileManager.latest_file(dir_path, ".tar.gz")
        if media_file:
            url = f"{MEDIA_BASE_URL}{user_id}/{media_file}"
            await context.bot.send_message(chat_id=user_id, text=f"📦 بکاپ مدیا آماده شد.\n💾 لینک: {url}")
        # نمایش لیست بکاپ‌ها به جای منوی اصلی
        await BackupManager.list_backups(user_id, context, backup_type="media")

    @staticmethod
    async def list_backups(user_id, context, backup_type=None):
        logger.debug(f"Listing backups for user {user_id}, type {backup_type}")
        if not backup_type:
            # منوی اصلی
            keyboard = [
                [InlineKeyboardButton("📁 بکاپ دیتابیس", callback_data="list_db_backups"),
                 InlineKeyboardButton("📁 بکاپ مدیا", callback_data="list_media_backups")]
            ]
            if BackupManager.is_super_admin(user_id):
                keyboard.append([
                    InlineKeyboardButton("📁 بکاپ دیتابیس سیستم", callback_data="list_system_db_backups"),
                    InlineKeyboardButton("📁 بکاپ مدیا سیستم", callback_data="list_system_media_backups")
                ])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="backup_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text="📦 بخش لیست بکاپ‌ها", reply_markup=reply_markup)
            return
        
        # لیست واقعی فایل‌ها
        is_system = backup_type.startswith("system_")
        effective_user_id = "system" if is_system else user_id
        effective_type = backup_type.replace("system_", "")

        if effective_type == "db":
            await BackupManager._list_db_backups(user_id, context, effective_user_id)
        elif effective_type == "media":
            await BackupManager._list_media_backups(user_id, context, effective_user_id)

    @staticmethod
    async def _list_db_backups(user_id, context, effective_user_id):
        dir_path = BackupManager.user_backup_dir(effective_user_id, "db")
        files = FileManager.list_latest_files(dir_path, ".sql", BackupManager.MAX_LIST)
        if not files:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ بکاپ دیتابیسی موجود نیست!")
            return
        keyboard = []
        is_system = effective_user_id == "system"
        message = "📦 آخرین بکاپ‌های دیتابیس:\n"
        for idx, file in enumerate(files, 1):
            file_path = os.path.join(dir_path, file)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # اندازه به مگابایت
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            message += f"{idx}. {file} (اندازه: {file_size:.2f} MB, زمان: {file_time})\n"
            row = [InlineKeyboardButton(f"{idx}. {file}", callback_data=f"send_db::{file_path}")]
            if not is_system:
                row.append(InlineKeyboardButton("🗑️", callback_data=f"delete_db::{file_path}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

    @staticmethod
    async def _list_media_backups(user_id, context, effective_user_id):
        dir_path = BackupManager.user_backup_dir(effective_user_id, "media")
        files = FileManager.list_latest_files(dir_path, ".tar.gz", BackupManager.MAX_LIST)
        if not files:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ بکاپ مدیایی موجود نیست!")
            return
        keyboard = []
        is_system = effective_user_id == "system"
        message = "📦 آخرین بکاپ‌های مدیا:\n"
        for idx, file in enumerate(files, 1):
            file_path = os.path.join(dir_path, file)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # اندازه به مگابایت
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            url = f"{MEDIA_BASE_URL}{effective_user_id}/{file}"
            message += f"{idx}. {file} (اندازه: {file_size:.2f} MB, زمان: {file_time})\n"
            row = [InlineKeyboardButton(f"{idx}. {file}", url=url)]
            if not is_system:
                row.append(InlineKeyboardButton("🗑️", callback_data=f"delete_media::{file_path}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

    @staticmethod
    async def handle_callback(user_id, context, callback_data):
        logger.debug(f"Received callback_data: {callback_data} for user {user_id}")
        try:
            if callback_data.startswith("send_db::"):
                file_path = callback_data.split("::")[1]
                await BackupManager.send_backup_file(user_id, context, file_path, "db")
            elif callback_data.startswith("send_media::"):
                file_path = callback_data.split("::")[1]
                await BackupManager.send_backup_file(user_id, context, file_path, "media")
            elif callback_data.startswith("delete_db::"):
                file_path = callback_data.split("::")[1]
                await BackupManager.delete_backup(user_id, context, file_path)
            elif callback_data.startswith("delete_media::"):
                file_path = callback_data.split("::")[1]
                await BackupManager.delete_backup(user_id, context, file_path)
            elif callback_data.startswith("list_"):
                backup_type = callback_data.replace("list_", "")
                await BackupManager.list_backups(user_id, context, backup_type=backup_type)
            elif callback_data == "backup_menu":
                await MenuManager.show_main_menu(user_id, context)
            else:
                logger.warning(f"Unknown callback_data: {callback_data}")
                await context.bot.send_message(chat_id=user_id, text="❌ دستور ناشناخته!")
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا: {str(e)}")
            # بازگشت به لیست بکاپ‌ها به جای منوی اصلی
            await BackupManager.list_backups(user_id, context)

    @staticmethod
    async def send_backup_file(user_id, context, file_path, backup_type):
        logger.debug(f"Sending backup file: {file_path} for user {user_id}")
        if backup_type == "db" and os.path.exists(file_path):
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"))
        elif backup_type == "media" and os.path.exists(file_path):
            effective_user_id = "system" if "/system/" in file_path else user_id
            url = f"{MEDIA_BASE_URL}{effective_user_id}/{os.path.basename(file_path)}"
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک: {url}")
        else:
            logger.error(f"File not found: {file_path}")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل یافت نشد!")

    @staticmethod
    async def delete_backup(user_id, context, file_path):
        logger.debug(f"Deleting backup file: {file_path} for user {user_id}")
        if "/system/" in file_path:
            await context.bot.send_message(chat_id=user_id, text="❌ بکاپ سیستم قابل حذف نیست!")
            return
        if os.path.exists(file_path):
            os.remove(file_path)
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ حذف شد!")
            # بروزرسانی لیست بعد از حذف
            backup_type = "db" if file_path.endswith(".sql") else "media"
            await BackupManager.list_backups(user_id, context, backup_type=backup_type)
        else:
            logger.error(f"File not found for deletion: {file_path}")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")