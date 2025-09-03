import os
import subprocess
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from file_manager import FileManager

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")

        # مسیر اسکریپت
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")

        # اجرای backup.sh با پارامتر db
        result = subprocess.run([backup_script, "db"], capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس:\n{result.stderr}")
            return

        # پیدا کردن آخرین فایل بکاپ دیتابیس
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        if not db_file:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ دیتابیس پیدا نشد!")
            return

        file_path = os.path.join(DB_BACKUP_DIR, db_file)
        await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
        await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل بکاپ دیتابیس \nFile: {db_file}")

        # پاکسازی بکاپ‌های قدیمی
        FileManager.cleanup_old_backups(DB_BACKUP_DIR)

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ مدیا...")

        # مسیر اسکریپت
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")

        # اجرای backup.sh با پارامتر media
        result = subprocess.run([backup_script, "media"], capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا:\n{result.stderr}")
            return

        # پیدا کردن آخرین فایل بکاپ مدیا
        media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        if not media_file:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ مدیا پیدا نشد!")
            return

        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)
        await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")

        # ارسال لینک دانلود
        media_url = f"{MEDIA_BASE_URL}{media_file}"
        await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}")

        # پاکسازی بکاپ‌های قدیمی
        FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR)
