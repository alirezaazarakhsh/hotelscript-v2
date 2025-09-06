import os
import subprocess
import asyncio
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from file_manager import FileManager
from menu_manager import MenuManager
import logging
from datetime import datetime
import pytz
from jdatetime import datetime as jdatetime

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تنظیم منطقه زمانی تهران
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")

        # ایجاد دایرکتوری بکاپ دیتابیس
        os.makedirs(DB_BACKUP_DIR, exist_ok=True)

        # تولید زمان شمسی برای نام فایل
        current_time = datetime.now(TEHRAN_TZ)
        logger.debug(f"Current time (Gregorian): {current_time}")
        shamsi_time = jdatetime.fromgregorian(datetime=current_time, locale='fa_IR')
        timestamp = shamsi_time.strftime("%Y-%m-%d -%H:%M")
        logger.debug(f"Generated timestamp (Shamsi before send): {timestamp}")

        # اجرای اسکریپت بکاپ دیتابیس با ارسال زمان شمسی (بدون دو نقطه برای سازگاری با فایل)
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        file_timestamp = shamsi_time.strftime("%Y-%m-%d-%H-%M")  # فرمت بدون دو نقطه برای نام فایل
        logger.debug(f"Running backup.sh for DB with timestamp {file_timestamp}: {backup_script}")
        result = subprocess.run(f"{backup_script} db {file_timestamp}", shell=True, capture_output=True, text=True)
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            await MenuManager.show_main_menu(user_id, context)
            return

        # پیدا کردن آخرین فایل بکاپ دیتابیس با نام شمسی
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        file_path = os.path.join(DB_BACKUP_DIR, db_file)

        if os.path.exists(file_path):
            formatted_time = timestamp  # استفاده از زمان شمسی با فرمت جدید
            logger.debug(f"Formatted time for display: {formatted_time}")
            await context.bot.send_message(chat_id=user_id, text=f"✅ بکاپ دیتابیس با موفقیت انجام شد. (time backup: {formatted_time})", parse_mode="Markdown")
            await context.bot.send_document(
                chat_id=user_id,
                document=open(file_path, "rb"),
                caption=f"فایل بکاپ دیتابیس\nFile: {db_file}\n{formatted_time}"
            )
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        FileManager.cleanup_old_backups(DB_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        
        # نمایش منوی اصلی
        await MenuManager.show_main_menu(user_id, context)
        logger.debug(f"Main menu displayed for user {user_id} after database backup")

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ مدیا...")

        # ایجاد دایرکتوری بکاپ مدیا
        os.makedirs(MEDIA_BACKUP_DIR, exist_ok=True)

        # تولید زمان شمسی برای نام فایل
        current_time = datetime.now(TEHRAN_TZ)
        logger.debug(f"Current time (Gregorian): {current_time}")
        shamsi_time = jdatetime.fromgregorian(datetime=current_time, locale='fa_IR')
        timestamp = shamsi_time.strftime("%Y-%m-%d -%H:%M")
        logger.debug(f"Generated timestamp (Shamsi before send): {timestamp}")

        # اجرای اسکریپت بکاپ مدیا با ارسال زمان شمسی (بدون دو نقطه برای سازگاری با فایل)
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        file_timestamp = shamsi_time.strftime("%Y-%m-%d-%H-%M")  # فرمت بدون دو نقطه برای نام فایل
        logger.debug(f"Running backup.sh for media with timestamp {file_timestamp}: {backup_script}")
        result = subprocess.run(f"{backup_script} media {file_timestamp}", shell=True, capture_output=True, text=True)
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "خطای ناشناخته در اجرای اسکریپت بکاپ"
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {error_msg}")
            await MenuManager.show_main_menu(user_id, context)
            return

        # پیدا کردن آخرین فایل بکاپ مدیا با نام شمسی
        media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)

        if os.path.exists(file_path):
            formatted_time = timestamp  # استفاده از زمان شمسی با فرمت جدید
            logger.debug(f"Formatted time for display: {formatted_time}")
            await context.bot.send_message(chat_id=user_id, text=f"✅ بکاپ مدیا با موفقیت انجام شد. (time backup: {formatted_time})", parse_mode="Markdown")
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}\n{formatted_time}", parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        
        # نمایش منوی اصلی
        await MenuManager.show_main_menu(user_id, context)
        logger.debug(f"Main menu displayed for user {user_id} after media backup")