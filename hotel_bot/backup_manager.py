import os
import subprocess
import asyncio
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from file_manager import FileManager
from menu_manager import MenuManager
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")

        # ایجاد دایرکتوری بکاپ دیتابیس
        os.makedirs(DB_BACKUP_DIR, exist_ok=True)

        # اجرای اسکریپت بکاپ دیتابیس
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        logger.debug(f"Running backup.sh for DB: {backup_script}")
        result = subprocess.run(f"{backup_script} db", shell=True, capture_output=True, text=True)
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            await MenuManager.show_main_menu(user_id, context)
            return

        # پیدا کردن آخرین فایل بکاپ دیتابیس
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        file_path = os.path.join(DB_BACKUP_DIR, db_file)

        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            await context.bot.send_document(
                chat_id=user_id,
                document=open(file_path, "rb"),
                caption=f"فایل بکاپ دیتابیس\nFile: {db_file}"
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

        # اجرای اسکریپت بکاپ مدیا
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        logger.debug(f"Running backup.sh for media: {backup_script}")
        result = subprocess.run(f"{backup_script} media", shell=True, capture_output=True, text=True)
        logger.debug(f"backup.sh stdout: {result.stdout}")
        logger.debug(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {result.stderr}")
            await MenuManager.show_main_menu(user_id, context)
            return

        # پیدا کردن آخرین فایل بکاپ مدیا
        media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)

        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        
        # نمایش منوی اصلی
        await MenuManager.show_main_menu(user_id, context)
        logger.debug(f"Main menu displayed for user {user_id} after media backup")