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
BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/backups/sf24_9xkLp7")
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
    zip_files = [f for f in files if f.endswith(".zip") or f.endswith(".tar.gz") or f.endswith(".sql")]
    while len(zip_files) > MAX_BACKUPS:
        oldest = zip_files.pop(0)
        os.remove(os.path.join(BACKUP_DIR, oldest))

def latest_file(extension=None):
    files = [f for f in os.listdir(BACKUP_DIR) if (extension is None or f.endswith(extension))]
    return sorted(files, reverse=True)[0] if files else None

# ======================== نمایش منوی اصلی ========================
async def show_main_menu(user_id, context: ContextTypes.DEFAULT_TYPE, message_id=None, chat_id=None, text_prefix=""):
    username = (await context.bot.get_chat_member(user_id=user_id, chat_id=user_id)).user.first_name
    text = f"""
👋 سلام ادمین عزیز {username}!

این ربات بکاپ و ریستور هتل شما را مدیریت می‌کند.

📌 قابلیت‌ها:
- 📦 بکاپ کامل: دیتابیس + مدیا
- 🖥 بکاپ جداگانه: فقط دیتابیس یا فقط مدیا
- 🗂 لیست بکاپ‌ها و ریستور جداگانه هر بخش
- 💬 پشتیبانی و تماس با ادمین
""" 
    text = text_prefix + text if text_prefix else text
    keyboard = [
        [InlineKeyboardButton("📦 بکاپ کامل", callback_data="backup_full")],
        [InlineKeyboardButton("🖥 بکاپ جداگانه", callback_data="backup_separate")],
        [InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id and chat_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

# ======================== فرمان شروع ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return
    await show_main_menu(user_id, context)

# ======================== مدیریت دکمه‌ها ========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    await query.answer()

    if not is_allowed(user_id):
        await query.edit_message_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return

    data = query.data

    # ---------------- بکاپ کامل ----------------
    if data == "backup_full":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ کامل...")
        subprocess.run(f"{PROJECT_DIR}/backup.sh", shell=True)
        latest_db = latest_file(".sql")
        latest_media = latest_file(".tar.gz")

        # ارسال فایل‌ها مستقیم به تلگرام
        if latest_db:
            await context.bot.send_document(chat_id=user_id, document=open(os.path.join(BACKUP_DIR, latest_db), "rb"))
        if latest_media:
            await context.bot.send_document(chat_id=user_id, document=open(os.path.join(BACKUP_DIR, latest_media), "rb"))

        cleanup_old_backups()
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id, text_prefix="✅ بکاپ کامل انجام شد.\n\n")

    # ---------------- بکاپ جداگانه ----------------
    elif data == "backup_separate":
        keyboard = [
            [InlineKeyboardButton("📦 بکاپ دیتابیس", callback_data="backup_db")],
            [InlineKeyboardButton("🖼 بکاپ مدیا", callback_data="backup_media")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📌 انتخاب نوع بکاپ:", reply_markup=reply_markup)

    elif data == "backup_db":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ دیتابیس...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        db_file = f"db_{DATE}.sql"
        subprocess.run(f"docker exec postgres_db pg_dump -U postgres safarname24 > {os.path.join(BACKUP_DIR, db_file)}", shell=True)
        await context.bot.send_document(chat_id=user_id, document=open(os.path.join(BACKUP_DIR, db_file), "rb"))
        cleanup_old_backups()
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id, text_prefix="✅ بکاپ دیتابیس انجام شد.\n\n")

    elif data == "backup_media":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ مدیا...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        media_file = f"media_{DATE}.tar.gz"
        subprocess.run(f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media", shell=True)
        await context.bot.send_document(chat_id=user_id, document=open(os.path.join(BACKUP_DIR, media_file), "rb"))
        cleanup_old_backups()
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id, text_prefix="✅ بکاپ مدیا انجام شد.\n\n")

    # ---------------- لیست بکاپ‌ها ----------------
    elif data == "list_backups":
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz") or f.endswith(".sql")], reverse=True)
        if not files:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("هیچ بکاپی موجود نیست.", reply_markup=reply_markup)
            return
        keyboard = [[InlineKeyboardButton(f, callback_data=f"select:{f}")] for f in files]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 بکاپ‌ها:", reply_markup=reply_markup)

    elif data.startswith("select:"):
        filename = data.split(":", 1)[1]
        keyboard = []
        if filename.endswith(".sql"):
            keyboard.append([InlineKeyboardButton("📦 ریستور دیتابیس", callback_data=f"restore_db:{filename}")])
        elif filename.endswith(".tar.gz"):
            keyboard.append([InlineKeyboardButton("🖼 ریستور مدیا", callback_data=f"restore_media:{filename}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="list_backups")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 انتخاب عملیات برای {filename}:", reply_markup=reply_markup)

    # ---------------- ریستور دیتابیس ----------------
    elif data.startswith("restore_db:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            await query.edit_message_text("❌ فایل پیدا نشد!")
            return
        await query.edit_message_text(f"⏳ در حال ریستور دیتابیس از {filename} ...")
        subprocess.run(f"{PROJECT_DIR}/restore.sh {file_path} dummy_media", shell=True)
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id, text_prefix=f"✅ ریستور دیتابیس انجام شد: {filename}\n\n")

    # ---------------- ریستور مدیا ----------------
    elif data.startswith("restore_media:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            await query.edit_message_text("❌ فایل پیدا نشد!")
            return
        await query.edit_message_text(f"⏳ در حال ریستور مدیا از {filename} ...")
        subprocess.run(f"{PROJECT_DIR}/restore.sh dummy_db {file_path}", shell=True)
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id, text_prefix=f"✅ ریستور مدیا انجام شد: {filename}\n\n")

    # ---------------- بازگشت به منوی اصلی ----------------
    elif data == "go_back":
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)

    # ---------------- پشتیبانی ----------------
    elif data == "support":
        keyboard = [
            [InlineKeyboardButton("📩 تماس با پشتیبانی", url="https://t.me/sevintmadmin")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💬 برای پشتیبانی می‌توانید از دکمه زیر استفاده کنید:", reply_markup=reply_markup)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()