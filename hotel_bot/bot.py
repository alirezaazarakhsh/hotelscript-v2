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

# ================= توابع کمکی =================
def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def cleanup_old_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created BACKUP_DIR: {BACKUP_DIR}")
    files = sorted(os.listdir(BACKUP_DIR))
    zip_files = [f for f in files if f.endswith(".zip") or f.endswith(".tar.gz") or f.endswith(".sql")]
    while len(zip_files) > MAX_BACKUPS:
        oldest = zip_files.pop(0)
        os.remove(os.path.join(BACKUP_DIR, oldest))
        print(f"Removed old backup: {oldest}")

def latest_file(extension=None):
    files = [f for f in os.listdir(BACKUP_DIR) if (extension is None or f.endswith(extension))]
    return sorted(files, reverse=True)[0] if files else None

def get_file_datetime(filename):
    try:
        date_part = filename.split('_')[1] + '_' + filename.split('_')[2].split('.')[0]
        return datetime.strptime(date_part, "%Y-%m-%d_%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "نامشخص"

# ================= نمایش منوی اصلی =================
async def show_main_menu(user_id, context: ContextTypes.DEFAULT_TYPE, message_id=None, chat_id=None):
    username = (await context.bot.get_chat_member(user_id=user_id, chat_id=user_id)).user.first_name
    text = f"""
👋 سلام ادمین عزیز {username}!

📌 قابلیت‌ها:
- 📦 بکاپ کامل: دیتابیس + مدیا
- 🖥 بکاپ جداگانه
- 🗂 لیست بکاپ‌ها و ریستور
- 💬 پشتیبانی
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

# ================= فرمان start =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return
    await show_main_menu(user_id, context)

# ================= مدیریت دکمه‌ها =================
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
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ کامل...")
        result = subprocess.run(f"{PROJECT_DIR}/backup.sh", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ کامل: {result.stderr}")
            return

        latest_db = latest_file(".sql")
        latest_media = latest_file(".tar.gz")

        for f, desc in [(latest_db, "دیتابیس"), (latest_media, "مدیا")]:
            if f:
                try:
                    file_path = os.path.join(BACKUP_DIR, f)
                    with open(file_path, "rb") as file:
                        await context.bot.send_document(chat_id=user_id, document=file, caption=f"فایل {desc}: {f}")
                except Exception as e:
                    await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل {desc}: {e}")

        cleanup_old_backups()
        await show_main_menu(user_id, context)

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
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ دیتابیس...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        db_file = f"db_{DATE}.sql"
        result = subprocess.run(f"docker exec postgres_db pg_dump -U postgres safarname24 > {os.path.join(BACKUP_DIR, db_file)}", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            return
        try:
            file_path = os.path.join(BACKUP_DIR, db_file)
            with open(file_path, "rb") as f:
                await context.bot.send_document(chat_id=user_id, document=f, caption=f"فایل دیتابیس: {db_file}")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل دیتابیس: {e}")
        cleanup_old_backups()
        await show_main_menu(user_id, context)

    elif data == "backup_media":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ مدیا...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        media_file = f"media_{DATE}.tar.gz"
        result = subprocess.run(f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {result.stderr}")
            return
        try:
            file_path = os.path.join(BACKUP_DIR, media_file)
            with open(file_path, "rb") as f:
                await context.bot.send_document(chat_id=user_id, document=f, caption=f"فایل مدیا: {media_file}")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل مدیا: {e}")
        cleanup_old_backups()
        await show_main_menu(user_id, context)

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
        keyboard = []
        for f in files:
            file_datetime = get_file_datetime(f)
            keyboard.append([InlineKeyboardButton(f"{f} ({file_datetime})", callback_data=f"select:{f}"),
                             InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 لیست بکاپ‌ها:", reply_markup=reply_markup)

    elif data.startswith("delete:"):
        filename = data.split("delete:")[1]
        try:
            os.remove(os.path.join(BACKUP_DIR, filename))
            await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} حذف شد.")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در حذف فایل: {e}")
        await show_main_menu(user_id, context)

    elif data.startswith("select:"):
        filename = data.split("select:")[1]
        try:
            file_path = os.path.join(BACKUP_DIR, filename)
            with open(file_path, "rb") as f:
                await context.bot.send_document(chat_id=user_id, document=f, caption=f"فایل انتخاب شده: {filename}")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل: {e}")

    elif data == "backup_info":
        await context.bot.send_message(chat_id=user_id, text="📌 توضیحات بکاپ‌گیری:\n- بکاپ دیتابیس با فرمت SQL\n- بکاپ مدیا با فرمت tar.gz\n- حداکثر 7 بکاپ نگهداری می‌شود")

    elif data == "support":
        await context.bot.send_message(chat_id=user_id, text="💬 پشتیبانی: @your_support_username")

    elif data == "go_back":
        await show_main_menu(user_id, context)

# ================= اجرای ربات =================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()
