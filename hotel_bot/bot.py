import os
import subprocess
from datetime import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
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

# دیباگ: چاپ مسیرهای اصلی
print(f"PROJECT_DIR: {PROJECT_DIR}")
print(f"BACKUP_DIR: {BACKUP_DIR}")
print(f"Checking if BACKUP_DIR exists: {os.path.exists(BACKUP_DIR)}")
print(f"Checking if PROJECT_DIR exists: {os.path.exists(PROJECT_DIR)}")

# ================= حذف webhook برای جلوگیری از Conflict =================
async def delete_webhook():
    bot = Bot(token=TOKEN)
    await bot.delete_webhook()
    print("Webhook deleted to avoid conflict.")

asyncio.get_event_loop().run_until_complete(delete_webhook())

# ===========================================================
def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def cleanup_old_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created BACKUP_DIR: {BACKUP_DIR}")
    files = sorted(os.listdir(BACKUP_DIR))
    zip_files = [f for f in files if f.endswith(".zip") or f.endswith(".tar.gz") or f.endswith(".sql")]
    print(f"Backup files found: {zip_files}")
    while len(zip_files) > MAX_BACKUPS:
        oldest = zip_files.pop(0)
        print(f"Removing old backup: {oldest}")
        os.remove(os.path.join(BACKUP_DIR, oldest))

def latest_file(extension=None):
    files = [f for f in os.listdir(BACKUP_DIR) if (extension is None or f.endswith(extension))]
    print(f"Files with extension {extension}: {files}")
    return sorted(files, reverse=True)[0] if files else None

def get_file_datetime(filename):
    try:
        date_part = filename.split('_')[1] + '_' + filename.split('_')[2].split('.')[0]
        return datetime.strptime(date_part, "%Y-%m-%d_%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "نامشخص"

# ======================== نمایش منوی اصلی ========================
async def show_main_menu(user_id, context: ContextTypes.DEFAULT_TYPE, message_id=None, chat_id=None):
    username = (await context.bot.get_chat_member(user_id=user_id, chat_id=user_id)).user.first_name
    text = f"""
👋 سلام ادمین عزیز {username}!

این ربات بکاپ و ریستور هتل شما را مدیریت می‌کند.

📌 قابلیت‌ها:
- 📦 بکاپ کامل: دیتابیس + مدیا
- 🖥 بکاپ جداگانه: فقط دیتابیس یا فقط مدیا
- 🗂 لیست بکاپ‌ها و ریستور جداگانه هر بخش
- 💬 پشتیبانی و تماس با ادمین
- 📋 توضیحات بکاپ‌گیری
"""
    keyboard = [
        [InlineKeyboardButton("📦 بکاپ کامل", callback_data="backup_full")],
        [InlineKeyboardButton("🖥 بکاپ جداگانه", callback_data="backup_separate")],
        [InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
        [InlineKeyboardButton("📋 توضیحات بکاپ‌گیری", callback_data="backup_info")],
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

    # ---------- مثال برای backup کامل ----------
    if data == "backup_full":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ کامل...")
        result = subprocess.run(f"{PROJECT_DIR}/backup.sh", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")
        
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ کامل: {result.stderr}")
            return

        latest_db = latest_file(".sql")
        latest_media = latest_file(".tar.gz")

        if latest_db:
            try:
                file_path = os.path.join(BACKUP_DIR, latest_db)
                print(f"Sending DB file: {file_path}")
                with open(file_path, "rb") as f:
                    await context.bot.send_document(chat_id=user_id, document=f, caption=f"فایل دیتابیس: {latest_db}")
            except Exception as e:
                print(f"Error sending DB file: {e}")
                await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل دیتابیس: {e}")
        if latest_media:
            try:
                file_path = os.path.join(BACKUP_DIR, latest_media)
                print(f"Sending Media file: {file_path}")
                with open(file_path, "rb") as f:
                    await context.bot.send_document(chat_id=user_id, document=f, caption=f"فایل مدیا: {latest_media}")
            except Exception as e:
                print(f"Error sending Media file: {e}")
                await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل مدیا: {e}")
        
        cleanup_old_backups()
        await show_main_menu(user_id, context)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()
