import os
import subprocess
import logging
import shutil
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
        """چک کردن سوپر ادمین بودن کاربر"""
        return user_id in SUPER_ADMINS

    @staticmethod
    def user_backup_dir(user_id, backup_type):
        """تولید مسیر ذخیره بکاپ برای کاربر یا سیستم"""
        user_id_str = str(user_id) if user_id != "system" else "system"
        if backup_type == "db":
            return os.path.join(DB_BACKUP_DIR, user_id_str)
        elif backup_type == "media":
            return os.path.join(MEDIA_BACKUP_DIR, user_id_str)
        return None

    @staticmethod
    def get_timestamp():
        """گرفتن زمان به فرمت شمسی"""
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
                start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
                for user_dir in os.listdir(base_dir):
                    user_path = os.path.join(base_dir, user_dir)
                    if not os.path.isdir(user_path):
                        continue
                    for file_name in os.listdir(user_path):
                        file_path = os.path.join(user_path, file_name)
                        if os.path.isfile(file_path):
                            try:
                                date_str = file_name.split('_')[1].split('.')[0]
                                file_date = datetime.strptime(date_str, "%Y-%m-%d-%H-%M")
                                if file_date < start_of_week:
                                    os.remove(file_path)
                                    logger.info(f"Removed old weekly backup: {file_path}")
                            except (IndexError, ValueError):
                                continue
        except Exception as e:
            logger.error(f"Error in weekly cleanup: {e}")

    @staticmethod
    async def weekly_auto_backup():
        """بکاپ هفتگی اتوماتیک"""
        try:
            timestamp = BackupManager.get_timestamp()
            backup_script = os.path.join(PROJECT_DIR, "backup.sh")
            # بکاپ دیتابیس
            result = subprocess.run(f"{backup_script} db auto_{timestamp['file']} system", 
                                  shell=True, capture_output=True, text=True)
            logger.info(f"Weekly DB backup result: {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Weekly DB backup failed: {result.stderr}")
            # بکاپ مدیا
            result = subprocess.run(f"{backup_script} media auto_{timestamp['file']} system", 
                                  shell=True, capture_output=True, text=True)
            logger.info(f"Weekly media backup result: {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Weekly media backup failed: {result.stderr}")
            # پاکسازی قدیمی‌ها
            FileManager.cleanup_old_backups(BackupManager.user_backup_dir("system", "db"), max_files=BackupManager.WEEKLY_LIMIT)
            FileManager.cleanup_old_backups(BackupManager.user_backup_dir("system", "media"), max_files=BackupManager.WEEKLY_LIMIT)
        except Exception as e:
            logger.error(f"Error in weekly auto backup: {e}")

    @staticmethod
    async def backup_database(user_id, context):
        """بکاپ‌گیری از دیتابیس"""
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
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ‌گیری دیتابیس: {result.stderr}")
            return
        logger.debug(f"DB backup stdout: {result.stdout}, stderr: {result.stderr}")

        db_file = FileManager.latest_file(dir_path, ".sql")
        if db_file:
            await context.bot.send_document(chat_id=user_id,
                                          document=open(os.path.join(dir_path, db_file), "rb"),
                                          caption=f"📦 بکاپ دیتابیس\n{timestamp['display']}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ دیتابیس یافت نشد!")
        
        FileManager.cleanup_old_backups(dir_path, max_files=BackupManager.WEEKLY_LIMIT)
        await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def backup_media(user_id, context):
        """بکاپ‌گیری از مدیا"""
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
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در بکاپ‌گیری مدیا: {result.stderr}")
            return
        logger.debug(f"Media backup stdout: {result.stdout}, stderr: {result.stderr}")

        media_file = FileManager.latest_file(dir_path, ".tar.gz")
        if media_file:
            url = f"{MEDIA_BASE_URL}{user_id}/{media_file}"
            await context.bot.send_message(chat_id=user_id, text=f"📦 بکاپ مدیا آماده شد.\n💾 لینک: {url}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ مدیا یافت نشد!")
        
        FileManager.cleanup_old_backups(dir_path, max_files=BackupManager.WEEKLY_LIMIT)
        await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def list_backups(user_id, context, backup_type=None, chat_id=None, message_id=None):
        """نمایش لیست بکاپ‌ها با امکان فیلتر بر اساس نوع"""
        query = context._user_context_data.get('query')  # Access the callback query if available
        if not backup_type:
            text = ("📦 بخش لیست بکاپ‌ها\n\n"
                    "در این بخش می‌توانید حداکثر ۷ بکاپ جدید را مشاهده کنید. "
                    "بکاپ‌های قدیمی‌تر به طور خودکار پاک می‌شوند.\n"
                    "با کلیک روی نام فایل، می‌توانید فایل دیتابیس را دانلود یا لینک مدیا را دریافت کنید.\n"
                    "با کلیک روی 🗑️، فایل حذف می‌شود (فقط بکاپ‌های کاربر).")
            keyboard = [
                [
                    InlineKeyboardButton("📁 بکاپ دیتابیس", callback_data="list_db_backups"),
                    InlineKeyboardButton("📁 بکاپ مدیا", callback_data="list_media_backups")
                ]
            ]
            if BackupManager.is_super_admin(user_id):
                keyboard.append([
                    InlineKeyboardButton("📁 بکاپ دیتابیس سیستم", callback_data="list_system_db_backups"),
                    InlineKeyboardButton("📁 بکاپ مدیا سیستم", callback_data="list_system_media_backups")
                ])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="backup_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query and chat_id and message_id:
                await query.edit_message_text(text=text, reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
            return
        
        is_system = backup_type.startswith("system_")
        effective_user_id = "system" if is_system else user_id
        effective_backup_type = backup_type.replace("system_", "")
        
        if effective_backup_type == "db":
            await BackupManager._list_db_backups(user_id, context, effective_user_id, chat_id, message_id)
        elif effective_backup_type == "media":
            await BackupManager._list_media_backups(user_id, context, effective_user_id, chat_id, message_id)

    @staticmethod
    async def _list_db_backups(user_id, context, effective_user_id, chat_id=None, message_id=None):
        """لیست بکاپ‌های دیتابیس"""
        dir_path = BackupManager.user_backup_dir(effective_user_id, "db")
        db_files = FileManager.list_latest_files(dir_path, ".sql", BackupManager.MAX_LIST)
        
        if not db_files:
            text = "❌ هیچ بکاپ دیتابیسی موجود نیست!"
            query = context._user_context_data.get('query')
            if query and chat_id and message_id:
                await query.edit_message_text(text=text)
            else:
                await context.bot.send_message(chat_id=user_id, text=text)
            return
        
        keyboard = []
        is_system = effective_user_id == "system"
        for idx, file_name in enumerate(db_files, 1):
            file_path = os.path.join(dir_path, file_name)
            file_datetime = FileManager.get_file_datetime(file_name)
            row = [InlineKeyboardButton(f"{idx}. {file_name} ({file_datetime})", callback_data=f"send_db::{file_path}")]
            if not is_system:
                row.append(InlineKeyboardButton("🗑️", callback_data=f"delete_db::{file_path}"))
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📦 آخرین بکاپ‌های دیتابیس{' سیستم' if is_system else ''}:"
        query = context._user_context_data.get('query')
        if query and chat_id and message_id:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

    @staticmethod
    async def _list_media_backups(user_id, context, effective_user_id, chat_id=None, message_id=None):
        """لیست بکاپ‌های مدیا"""
        dir_path = BackupManager.user_backup_dir(effective_user_id, "media")
        media_files = FileManager.list_latest_files(dir_path, ".tar.gz", BackupManager.MAX_LIST)
        
        if not media_files:
            text = "❌ هیچ بکاپ مدیایی موجود نیست!"
            query = context._user_context_data.get('query')
            if query and chat_id and message_id:
                await query.edit_message_text(text=text)
            else:
                await context.bot.send_message(chat_id=user_id, text=text)
            return
        
        keyboard = []
        is_system = effective_user_id == "system"
        for idx, file_name in enumerate(media_files, 1):
            file_path = os.path.join(dir_path, file_name)
            file_datetime = FileManager.get_file_datetime(file_name)
            url = f"{MEDIA_BASE_URL}{effective_user_id}/{file_name}"
            row = [InlineKeyboardButton(f"{idx}. {file_name} ({file_datetime})", url=url)]
            if not is_system:
                row.append(InlineKeyboardButton("🗑️", callback_data=f"delete_media::{file_path}"))
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📦 آخرین بکاپ‌های مدیا{' سیستم' if is_system else ''}:"
        query = context._user_context_data.get('query')
        if query and chat_id and message_id:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

    @staticmethod
    async def send_backup_file(user_id, context, file_path, backup_type):
        """ارسال مجدد فایل بکاپ"""
        try:
            if backup_type == "db" and os.path.exists(file_path):
                file_datetime = FileManager.get_file_datetime(os.path.basename(file_path))
                await context.bot.send_document(
                    chat_id=user_id,
                    document=open(file_path, "rb"),
                    caption=f"📦 بکاپ دیتابیس\n{file_datetime}"
                )
            elif backup_type == "media" and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                file_datetime = FileManager.get_file_datetime(file_name)
                # Assuming effective_user_id from file_path
                effective_user_id = "system" if "/system/" in file_path else user_id
                url = f"{MEDIA_BASE_URL}{effective_user_id}/{file_name}"
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"📦 بکاپ مدیا\n{file_datetime}\n💾 لینک: {url}"
                )
            else:
                await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ یافت نشد!")
                logger.warning(f"Backup file not found at: {file_path}")
        except Exception as e:
            logger.error(f"Error sending backup file: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل بکاپ: {str(e)}")

    @staticmethod
    async def delete_backup(user_id, context, file_path):
        """حذف فایل بکاپ"""
        try:
            if "/system/" in file_path:
                await context.bot.send_message(chat_id=user_id, text="❌ بکاپ‌های سیستم قابل حذف نیستند!")
                return
            if os.path.exists(file_path):
                os.remove(file_path)
                await context.bot.send_message(chat_id=user_id, text="✅ بکاپ با موفقیت حذف شد!")
                backup_type = "db" if file_path.endswith(".sql") else "media"
                effective_user_id = user_id  # Since system backups can't be deleted
                if backup_type == "db":
                    await BackupManager._list_db_backups(user_id, context, effective_user_id)
                else:
                    await BackupManager._list_media_backups(user_id, context, effective_user_id)
            else:
                await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ یافت نشد!")
                logger.warning(f"Attempted to delete non-existent file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در حذف بکاپ: {str(e)}")