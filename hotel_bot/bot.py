import os
import subprocess
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# ================= بارگذاری متغیرهای محیطی =================
ENV_PATH = "/app/hotel_bot/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"⚠️ فایل .env پیدا نشد در مسیر {ENV_PATH}")

PROJECT_DIR = os.getenv("PROJECT_DIR", "/var/hotelscript-v2")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/backups/safarnameh")
BASE_URL = os.getenv("BASE_URL", "https://yourdomain.com/backups")
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
        [InlineKeyboardButton("📦 بکاپ کامل بگیر", callback_data="backup_full")],
        [InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
        [InlineKeyboardButton("🖥 بکاپ جداگانه", callback_data="backup_separate")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
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

    data = query.data

    # ==================== بکاپ کامل ====================
    if data == "backup_full":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ کامل...")
        subprocess.run(f"{PROJECT_DIR}/backup.sh", shell=True)
        # آخرین فایل zip در پوشه
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")], reverse=True)
        if files:
            latest = files[0]
            url = f"{BASE_URL}/{latest}"
            await query.edit_message_text(f"✅ بکاپ کامل گرفته شد!\n[دانلود فایل بکاپ]({url})", parse_mode="Markdown")
        cleanup_old_backups()

    # ==================== لیست بکاپ‌ها ====================
    elif data == "list_backups":
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")], reverse=True)
        if not files:
            await query.edit_message_text("هیچ بکاپی موجود نیست.")
            return
        keyboard = [[InlineKeyboardButton(f, callback_data=f"select:{f}")] for f in files]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 بکاپ‌ها:", reply_markup=reply_markup)

    # ==================== انتخاب بکاپ برای ریستور ====================
    elif data.startswith("select:"):
        filename = data.split(":", 1)[1]
        keyboard = [
            [InlineKeyboardButton("📦 ریستور دیتابیس", callback_data=f"restore_db:{filename}")],
            [InlineKeyboardButton("🖼 ریستور مدیا", callback_data=f"restore_media:{filename}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 انتخاب عملیات برای {filename}:", reply_markup=reply_markup)

    # ==================== ریستور دیتابیس ====================
    elif data.startswith("restore_db:"):
        filename = data.split(":", 1)[1]
        zip_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(zip_path):
            await query.edit_message_text("❌ فایل زیپ پیدا نشد!")
            return
        await query.edit_message_text(f"⏳ در حال ریستور دیتابیس از {filename} ...")
        subprocess.run(f"{PROJECT_DIR}/restore.sh {BACKUP_DIR}/db.sql dummy_media", shell=True)
        await query.edit_message_text(f"✅ ریستور دیتابیس انجام شد: {filename}")

    # ==================== ریستور مدیا ====================
    elif data.startswith("restore_media:"):
        filename = data.split(":", 1)[1]
        zip_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(zip_path):
            await query.edit_message_text("❌ فایل زیپ پیدا نشد!")
            return
        await query.edit_message_text(f"⏳ در حال ریستور مدیا از {filename} ...")
        subprocess.run(f"{PROJECT_DIR}/restore.sh dummy_db {BACKUP_DIR}/media.tar.gz", shell=True)
        await query.edit_message_text(f"✅ ریستور مدیا انجام شد: {filename}")

    # ==================== بکاپ جداگانه ====================
    elif data == "backup_separate":
        keyboard = [
            [InlineKeyboardButton("📦 بکاپ دیتابیس", callback_data="backup_db")],
            [InlineKeyboardButton("🖼 بکاپ مدیا", callback_data="backup_media")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📌 انتخاب نوع بکاپ:", reply_markup=reply_markup)

    elif data == "backup_db":
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        db_file = f"db_{DATE}.sql"
        subprocess.run(f"docker exec postgres_db pg_dump -U postgres safarname24 > {os.path.join(BACKUP_DIR, db_file)}", shell=True)
        url = f"{BASE_URL}/{db_file}"
        await query.edit_message_text(f"✅ بکاپ دیتابیس گرفته شد!\n[دانلود فایل]({url})", parse_mode="Markdown")
        cleanup_old_backups()

    elif data == "backup_media":
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        media_file = f"media_{DATE}.tar.gz"
        subprocess.run(f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media", shell=True)
        url = f"{BASE_URL}/{media_file}"
        await query.edit_message_text(f"✅ بکاپ مدیا گرفته شد!\n[دانلود فایل]({url})", parse_mode="Markdown")
        cleanup_old_backups()

    # ==================== پشتیبانی ====================
    elif data == "support":
        keyboard = [[InlineKeyboardButton("📩 تماس با پشتیبانی", url="https://t.me/sevintmadmin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💬 کاربر عزیز سلام به درگاه پشتیبانی اسکریپت هتل خوش آمدید اگر مشکل فنی در زمینه بکاپ گیری دارید می توانید از طریق دکمه زیر به کارشناس پشتیبانی ما متصل بشید :", reply_markup=reply_markup)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()
