import os
import subprocess
import asyncio
import logging
from datetime import datetime
import pytz
from jdatetime import datetime as jdatetime
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from menu_manager import MenuManager

# تنظیم لاگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تنظیم منطقه زمانی تهران
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")

        if not os.path.exists(DB_BACKUP_DIR):
            logger.error(f"Database backup directory does not exist: {DB_BACKUP_DIR}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا: دایرکتوری {DB_BACKUP_DIR} وجود ندارد!")
            await MenuManager.show_main_menu(user_id, context)
            return

        # تولید زمان شمسی
        current_time = datetime.now(TEHRAN_TZ)
        shamsi_time = jdatetime.fromgregorian(datetime=current_time, locale='fa_IR')
        timestamp = shamsi_time.strftime("%Y-%m-%d -%H:%M")
        file_timestamp = shamsi_time.strftime("%Y-%m-%d-%H-%M")
        logger.debug(f"Generated timestamp (Shamsi): {file_timestamp}")

        # تنظیم رمز عبور دیتابیس
        os.environ["DB_PASSWORD"] = "admin"  # از .env گرفته شده

        # اجرای اسکریپت بکاپ
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        logger.debug(f"Running backup.sh for DB: {backup_script} db {file_timestamp}")
        result = subprocess.run(
            f"{backup_script} db {file_timestamp}",
            shell=True,
            capture_output=True,
            text=True
        )
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}"
            )
            await MenuManager.show_main_menu(user_id, context)
            return

        # انتظار برای اطمینان از ایجاد فایل
        for _ in range(5):  # حداکثر 5 ثانیه صبر کن
            db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
            if db_file:
                break
            await asyncio.sleep(1)  # تأخیر 1 ثانیه

        if not db_file:
            logger.error("No database backup file found!")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ دیتابیس پیدا نشد!")
            await MenuManager.show_main_menu(user_id, context)
            return

        file_path = os.path.join(DB_BACKUP_DIR, db_file)
        if os.path.exists(file_path):
            formatted_time = timestamp
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ بکاپ دیتابیس با موفقیت انجام شد. (time backup: {formatted_time})",
                parse_mode="Markdown"
            )
            await context.bot.send_document(
                chat_id=user_id,
                document=open(file_path, "rb"),
                caption=f"فایل بکاپ دیتابیس\nFile: {db_file}\n{formatted_time}"
            )
        else:
            logger.error(f"Backup file does not exist at {file_path}")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ دیتابیس پیدا نشد!")

        FileManager.cleanup_old_backups(DB_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ مدیا...")

        if not os.path.exists(MEDIA_BACKUP_DIR):
            logger.error(f"Media backup directory does not exist: {MEDIA_BACKUP_DIR}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا: دایرکتوری {MEDIA_BACKUP_DIR} وجود ندارد!")
            await MenuManager.show_main_menu(user_id, context)
            return

        # تولید زمان شمسی
        current_time = datetime.now(TEHRAN_TZ)
        shamsi_time = jdatetime.fromgregorian(datetime=current_time, locale='fa_IR')
        timestamp = shamsi_time.strftime("%Y-%m-%d -%H:%M")
        file_timestamp = shamsi_time.strftime("%Y-%m-%d-%H-%M")
        logger.debug(f"Generated timestamp (Shamsi): {file_timestamp}")

        # اجرای اسکریپت بکاپ
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        logger.debug(f"Running backup.sh for media: {backup_script} media {file_timestamp}")
        result = subprocess.run(
            f"{backup_script} media {file_timestamp}",
            shell=True,
            capture_output=True,
            text=True
        )
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "خطای ناشناخته در اجرای اسکریپت بکاپ"
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ خطا در گرفتن بکاپ مدیا: {error_msg}"
            )
            await MenuManager.show_main_menu(user_id, context)
            return

        # انتظار برای اطمینان از ایجاد فایل
        for _ in range(5):  # حداکثر 5 ثانیه صبر کن
            media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
            if media_file:
                break
            await asyncio.sleep(1)  # تأخیر 1 ثانیه

        if not media_file:
            logger.error("No media backup file found!")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ مدیا پیدا نشد!")
            await MenuManager.show_main_menu(user_id, context)
            return

        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)
        if os.path.exists(file_path):
            formatted_time = timestamp
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ بکاپ مدیا با موفقیت انجام شد. (time backup: {formatted_time})",
                parse_mode="Markdown"
            )
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(
                chat_id=user_id,
                text=f"💾 لینک دانلود: {media_url}\n{formatted_time}",
                parse_mode="Markdown"
            )
        else:
            logger.error(f"Backup file does not exist at {file_path}")
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ مدیا پیدا نشد!")

        FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        await MenuManager.show_main_menu(user_id, context)