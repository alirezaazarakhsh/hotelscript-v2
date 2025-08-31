import os
import subprocess
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import zipfile

# ================= بارگذاری متغیرهای محیطی =================
ENV_PATH = "/app/hotel_bot/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"⚠️ فایل .env پیدا نشد در مسیر {ENV_PATH}")

PROJECT_DIR = os.getenv("PROJECT_DIR", "/var/hotelscript-v2")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/backups/safarnameh")
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = list(map(int, os.getenv("ALLOWED_USERS", "").split(",")))
MAX_BACKUPS = 7
# ===========================================================

def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def cleanup_old_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    files = sorted(os.listdir(BACKUP_DIR))
    zip_files = [f for f in files if f.endswith(".zip")]
    while len(zip_files) > MAX_BACKUPS:
        oldest = zip_files.pop(0)
        os.remove(os.path.join(BACKUP_DIR, oldest))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📦 بکاپ جدید بگیر", callback_data="backup_now")],
        [InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
        [InlineKeyboardButton("💬 پشتیبانی", url="https://t.me/sevintmadmin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("سلام! چه کاری میخوای انجام بدی؟", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not is_allowed(user_id):
        await query.edit_message_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return

    if query.data == "backup_now":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ...")

        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        db_file = f"db_{DATE}.sql"
        media_file = f"media_{DATE}.tar.gz"
        zip_file = f"backup_{DATE}.zip"
        zip_path = os.path.join(BACKUP_DIR, zip_file)

        # بکاپ دیتابیس
        subprocess.run(f"docker exec postgres_db pg_dump -U postgres safarname24 > {os.path.join(BACKUP_DIR, db_file)}", shell=True)
        # بکاپ مدیا
        subprocess.run(f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media", shell=True)

        # زیپ کردن هر دو
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(os.path.join(BACKUP_DIR, db_file), db_file)
            zf.write(os.path.join(BACKUP_DIR, media_file), media_file)

        os.remove(os.path.join(BACKUP_DIR, db_file))
        os.remove(os.path.join(BACKUP_DIR, media_file))
        cleanup_old_backups()

        await query.edit_message_text(
            f"✅ بکاپ گرفته شد!\nفایل زیپ: `{zip_file}`\nلینک دانلود را از FTP یا ابزار مشابه دریافت کنید."
        )

    elif query.data == "list_backups":
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")], reverse=True)
        if not files:
            await query.edit_message_text("هیچ بکاپی موجود نیست.")
            return

        keyboard = [[InlineKeyboardButton(f, callback_data=f"restore:{f}")] for f in files]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 بکاپ‌ها:", reply_markup=reply_markup)

    elif query.data.startswith("restore:"):
        filename = query.data.split(":", 1)[1]
        zip_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(zip_path):
            await query.edit_message_text("❌ فایل زیپ پیدا نشد!")
            return

        await query.edit_message_text(f"⏳ در حال ریستور بکاپ {filename} ...")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(BACKUP_DIR)
            extracted_files = zf.namelist()

        db_file = next((f for f in extracted_files if f.endswith(".sql")), None)
        media_file = next((f for f in extracted_files if f.endswith(".tar.gz")), None)

        if db_file:
            db_path = os.path.join(BACKUP_DIR, db_file)
            subprocess.run(f"cat {db_path} | docker exec -i postgres_db psql -U postgres safarname24", shell=True)
            os.remove(db_path)

        if media_file:
            media_path = os.path.join(BACKUP_DIR, media_file)
            subprocess.run(f"tar -xzf {media_path} -C {PROJECT_DIR}", shell=True)
            os.remove(media_path)

        await query.edit_message_text(f"🔄 ریستور انجام شد: {filename}")

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()
