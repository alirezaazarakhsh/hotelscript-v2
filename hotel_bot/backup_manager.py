import os
import subprocess
import asyncio
from config import PROJECT_DIR, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MEDIA_BASE_URL
from file_manager import FileManager

class BackupManager:
    @staticmethod
    async def backup_database(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")

        # بررسی وجود backup.sh
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        if not os.path.exists(backup_script):
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا: فایل {backup_script} پیدا نشد!")
            return

        # ایجاد دایرکتوری بکاپ دیتابیس
        os.makedirs(DB_BACKUP_DIR, exist_ok=True)

        # اجرای اسکریپت بکاپ دیتابیس با تایم‌اوت
        print(f"Running backup.sh for DB: {backup_script}")
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [backup_script, "db"],
                capture_output=True,
                text=True,
                timeout=300  # تایم‌اوت 5 دقیقه
            )
        except subprocess.TimeoutExpired:
            await context.bot.send_message(chat_id=user_id, text="❌ خطا: اجرای بکاپ دیتابیس بیش از حد طول کشید!")
            return
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در اجرای اسکریپت بکاپ دیتابیس: {str(e)}")
            return

        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس:\n{result.stderr or 'خطای ناشناخته'}")
            return

        # پیدا کردن آخرین فایل بکاپ دیتابیس
        db_file = FileManager.latest_file(DB_BACKUP_DIR, extension=".sql")
        if not db_file:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ فایل بکاپ دیتابیسی پیدا نشد!")
            return

        file_path = os.path.join(DB_BACKUP_DIR, db_file)
        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            try:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=open(file_path, "rb"),
                    caption=f"فایل بکاپ دیتابیس\nFile: {db_file}"
                )
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل بکاپ: {str(e)}")
        else:
            await context.bot.send_message(chat_id=user_id, text=f"❌ فایل بکاپ {db_file} پیدا نشد!")

        # پاکسازی بکاپ‌های قدیمی
        try:
            FileManager.cleanup_old_backups(DB_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در پاکسازی بکاپ‌های قدیمی: {str(e)}")

    @staticmethod
    async def backup_media(user_id, context):
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ مدیا...")

        # بررسی وجود backup.sh
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        if not os.path.exists(backup_script):
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا: فایل {backup_script} پیدا نشد!")
            return

        # ایجاد دایرکتوری بکاپ مدیا
        os.makedirs(MEDIA_BACKUP_DIR, exist_ok=True)

        # اجرای اسکریپت بکاپ مدیا با تایم‌اوت
        print(f"Running backup.sh for media: {backup_script}")
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [backup_script, "media"],
                capture_output=True,
                text=True,
                timeout=600  # تایم‌اوت 10 دقیقه برای مدیا
            )
        except subprocess.TimeoutExpired:
            await context.bot.send_message(chat_id=user_id, text="❌ خطا: اجرای بکاپ مدیا بیش از حد طول کشید!")
            return
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در اجرای اسکریپت بکاپ مدیا: {str(e)}")
            return

        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا:\n{result.stderr or 'خطای ناشناخته'}")
            return

        # پیدا کردن آخرین فایل بکاپ مدیا
        media_file = FileManager.latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        if not media_file:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ فایل بکاپ مدیایی پیدا نشد!")
            return

        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)
        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}")
        else:
            await context.bot.send_message(chat_id=user_id, text=f"❌ فایل بکاپ {media_file} پیدا نشد!")

        # پاکسازی بکاپ‌های قدیمی
        try:
            FileManager.cleanup_old_backups(MEDIA_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="🧹 بکاپ‌های قدیمی مدیریت شدند.")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در پاکسازی بکاپ‌های قدیمی: {str(e)}")