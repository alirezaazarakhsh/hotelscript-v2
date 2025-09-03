import os
import subprocess
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from file_manager import FileManager
from menu_manager import MenuManager

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده سازی بکاپ دیتابیس...")
        
        # اجرای backup.sh
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        if not os.path.exists(DB_BACKUP_DIR):
            os.makedirs(DB_BACKUP_DIR)

        print(f"Running backup.sh for DB: {backup_script}")
        result = subprocess.run(f"{backup_script} db", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            return

        # پیدا کردن آخرین فایل بکاپ دیتابیس
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        file_path = os.path.join(DB_BACKUP_DIR, db_file)

        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل بکاپ دیتابیس \nFile: {db_file}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        FileManager.cleanup_old_backups(DB_BACKUP_DIR)

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده سازی بکاپ مدیا...")

        if not os.path.exists(MEDIA_BACKUP_DIR):
            os.makedirs(MEDIA_BACKUP_DIR)

        # اجرای backup.sh برای مدیا
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        result = subprocess.run(f"{backup_script} media", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {result.stderr}")
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