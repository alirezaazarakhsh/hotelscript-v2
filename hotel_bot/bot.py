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

# دیباگ: چاپ مسیرهای اصلی
print(f"PROJECT_DIR: {PROJECT_DIR}")
print(f"BACKUP_DIR: {BACKUP_DIR}")
print(f"Checking if BACKUP_DIR exists: {os.path.exists(BACKUP_DIR)}")
print(f"Checking if PROJECT_DIR exists: {os.path.exists(PROJECT_DIR)}")

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
    """استخراج تاریخ و زمان از نام فایل"""
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

    # ---------------- بکاپ کامل ----------------
    if data == "backup_full":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ کامل...")
        print(f"Running backup.sh from {PROJECT_DIR}/backup.sh")
        result = subprocess.run(f"{PROJECT_DIR}/backup.sh", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")
        
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ کامل: {result.stderr}")
            return

        latest_db = latest_file(".sql")
        latest_media = latest_file(".tar.gz")

        if latest_db or latest_media:
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ کامل با موفقیت انجام شد.")
            if latest_db:
                try:
                    file_path = os.path.join(BACKUP_DIR, latest_db)
                    print(f"Sending DB file: {file_path}")
                    await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل دیتابیس: {latest_db}")
                except Exception as e:
                    print(f"Error sending DB file: {e}")
                    await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل دیتابیس: {e}")
            if latest_media:
                try:
                    file_path = os.path.join(BACKUP_DIR, latest_media)
                    print(f"Sending Media file: {file_path}")
                    await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل مدیا: {latest_media}")
                except Exception as e:
                    print(f"Error sending Media file: {e}")
                    await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل مدیا: {e}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ هیچ فایلی برای ارسال یافت نشد.")
        
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
        print(f"Running pg_dump for {db_file}")
        result = subprocess.run(f"docker exec postgres_db pg_dump -U postgres safarname24 > {os.path.join(BACKUP_DIR, db_file)}", shell=True, capture_output=True, text=True)
        print(f"pg_dump stdout: {result.stdout}")
        print(f"pg_dump stderr: {result.stderr}")
        
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            return

        try:
            file_path = os.path.join(BACKUP_DIR, db_file)
            print(f"Sending DB file: {file_path}")
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل دیتابیس: {db_file}")
        except Exception as e:
            print(f"Error sending DB file: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل دیتابیس: {e}")
        
        cleanup_old_backups()
        await show_main_menu(user_id, context)

    elif data == "backup_media":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال گرفتن بکاپ مدیا...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        media_file = f"media_{DATE}.tar.gz"
        print(f"Running tar for {media_file}")
        result = subprocess.run(f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media", shell=True, capture_output=True, text=True)
        print(f"tar stdout: {result.stdout}")
        print(f"tar stderr: {result.stderr}")
        
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {result.stderr}")
            return

        try:
            file_path = os.path.join(BACKUP_DIR, media_file)
            print(f"Sending Media file: {file_path}")
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل مدیا: {media_file}")
        except Exception as e:
            print(f"Error sending Media file: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل مدیا: {e}")
        
        cleanup_old_backups()
        await show_main_menu(user_id, context)

    # ---------------- لیست بکاپ‌ها ----------------
    elif data == "list_backups":
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print(f"Created BACKUP_DIR: {BACKUP_DIR}")
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz") or f.endswith(".sql")], reverse=True)
        print(f"Listing backups: {files}")
        if not files:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("هیچ بکاپی موجود نیست.", reply_markup=reply_markup)
            return
        keyboard = []
        for f in files:
            file_datetime = get_file_datetime(f)
            keyboard.append([
                InlineKeyboardButton(f"{f} ({file_datetime})", callback_data=f"select:{f}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 بکاپ‌ها:", reply_markup=reply_markup)

    # ---------------- حذف بکاپ ----------------
    elif data.startswith("delete:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} با موفقیت حذف شد.")
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در حذف فایل {filename}: {e}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")
        await context.bot.send_message(chat_id=user_id, text="📁 لیست به‌روز شده بکاپ‌ها:")
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz") or f.endswith(".sql")], reverse=True)
        if not files:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text="هیچ بکاپی موجود نیست.", reply_markup=reply_markup)
            return
        keyboard = []
        for f in files:
            file_datetime = get_file_datetime(f)
            keyboard.append([
                InlineKeyboardButton(f"{f} ({file_datetime})", callback_data=f"select:{f}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text="📁 بکاپ‌ها:", reply_markup=reply_markup)

    # ---------------- انتخاب بکاپ ----------------
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
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")
            return
        await context.bot.send_message(chat_id=user_id, text=f"⏳ در حال ریستور دیتابیس از {filename} ...")
        result = subprocess.run(f"{PROJECT_DIR}/restore.sh {file_path} dummy_media", shell=True, capture_output=True, text=True)
        print(f"restore.sh stdout: {result.stdout}")
        print(f"restore.sh stderr: {result.stderr}")
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ریستور دیتابیس: {result.stderr}")
            return
        await context.bot.send_message(chat_id=user_id, text=f"✅ ریستور دیتابیس با موفقیت انجام شد: {filename}")
        await show_main_menu(user_id, context)

    # ---------------- ریستور مدیا ----------------
    elif data.startswith("restore_media:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")
            return
        await context.bot.send_message(chat_id=user_id, text=f"⏳ در حال ریستور مدیا از {filename} ...")
        result = subprocess.run(f"{PROJECT_DIR}/restore.sh dummy_db {file_path}", shell=True, capture_output=True, text=True)
        print(f"restore.sh stdout: {result.stdout}")
        print(f"restore.sh stderr: {result.stderr}")
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ریستور مدیا: {result.stderr}")
            return
        await context.bot.send_message(chat_id=user_id, text=f"✅ ریستور مدیا با موفقیت انجام شد: {filename}")
        await show_main_menu(user_id, context)

    # ---------------- توضیحات بکاپ‌گیری ----------------
    elif data == "backup_info":
        text = """
📋 **توضیحات بکاپ‌گیری روزانه**

این ربات به‌صورت روزانه بکاپ‌هایی از دیتابیس و فایل‌های مدیا شما ایجاد می‌کند. جزئیات:
- **بکاپ دیتابیس**: شامل تمام داده‌های دیتابیس safarname24 در قالب فایل .sql.
- **بکاپ مدیا**: شامل فایل‌های مدیا در قالب فایل فشرده .tar.gz.
- **حداکثر تعداد بکاپ‌ها**: {MAX_BACKUPS} فایل اخیر نگهداری می‌شود و فایل‌های قدیمی‌تر به‌صورت خودکار حذف می‌شوند.
- **ریستور**: امکان بازگردانی دیتابیس یا مدیا از بکاپ‌های موجود.

برای ارتقا تعداد درخواست‌های بکاپ‌گیری یا امکانات بیشتر، از دکمه زیر استفاده کنید.
        """.format(MAX_BACKUPS=MAX_BACKUPS)
        keyboard = [
            [InlineKeyboardButton("🚀 ارتقا تعداد درخواست‌ها", callback_data="upgrade_requests")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    # ---------------- ارتقا تعداد درخواست‌ها ----------------
    elif data == "upgrade_requests":
        await query.edit_message_text("🚀 در حال حاضر امکان ارتقا تعداد درخواست‌ها در دست توسعه است. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="backup_info")]]))

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