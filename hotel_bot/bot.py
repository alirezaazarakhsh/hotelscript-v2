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
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", "/var/lib/backsafarname/alirezaazarakhsh20_gmail.com")
MEDIA_BACKUP_DIR = os.getenv("MEDIA_BACKUP_DIR", "/var/backups/sf24_9xkLp7")
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = list(map(int, os.getenv("ALLOWED_USERS", "").split(",")))
MAX_BACKUPS = 7
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/sf24_9xkLp7/")

# ===========================================================

def is_allowed(user_id):
    return user_id in ALLOWED_USERS

def cleanup_old_backups(backup_dir):
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    files = sorted(os.listdir(backup_dir))
    zip_files = [f for f in files if f.endswith(".zip") or f.endswith(".tar.gz") or f.endswith(".sql")]
    while len(zip_files) > MAX_BACKUPS:
        oldest = zip_files.pop(0)
        os.remove(os.path.join(backup_dir, oldest))

def latest_file(backup_dir, extension=None):
    files = [f for f in os.listdir(backup_dir) if (extension is None or f.endswith(extension))]
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
سلام  {username}!
به ربات اسکریپت هتل خوش اومدی  👋🏻

در این نسخه از ربات تلاش کرده ایم تمامی نیاز های شما را پوشش دهیم و مدیریت اسکریپت را برای برطرف کنیم 
    
  امکانات ورژن 1.1 ربات\n

 📦 بکاپ گیری دستی از دیتابیس و پوشه مدیا \n
 🗂 نمایش لیست بکاپ‌ها با امکان حذف \n
 📮 پشتیبانی ارتباط سریع با ادمین \n
  📋 راهنمای بکاپ گیری (در حال توسعه ...)\n
"""
    keyboard = [
        [InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"),
         InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
        [InlineKeyboardButton("🗃 ریستور بکاپ", callback_data="restore_backup")],
        [InlineKeyboardButton("📋 نحوه بکاپ‌گیری", callback_data="backup_info"),
         InlineKeyboardButton("📮 پشتیبانی", callback_data="support")]
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
        await update.message.reply_text(
            "💢 دسترسی غیرفعال\n\n"
            "متأسفانه شما مجاز به استفاده از خدمات این ربات نیستید، در صورتی که از فعال بودن اشتراک خود مطمئن هستید، لطفاً دوباره تلاش کنید."
        )
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
        await query.edit_message_text(
            "💢 دسترسی غیرفعال\n\n"
            "متأسفانه شما مجاز به استفاده از خدمات این ربات نیستید، در صورتی که از فعال بودن اشتراک خود مطمئن هستید، لطفاً دوباره تلاش کنید."
        )
        return

    data = query.data

    # ---------------- منوی بکاپ ----------------
    if data == "backup_menu":
        text = "📦 انتخاب نوع بکاپ گیری \n\nلازم به ذکر می باشد که می توانید از دیتابیس یا فولدر های مدیا بکاپ بگیرید "
        keyboard = [
            [InlineKeyboardButton(" 2 - دیتابیس", callback_data="backup_db"),
             InlineKeyboardButton(" 1 - فولدر مدیا", callback_data="backup_media")],
            [InlineKeyboardButton(" بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # ---------------- بکاپ دیتابیس ----------------
    elif data == "backup_db":
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
        db_file = latest_file(DB_BACKUP_DIR, extension=".sql")
        file_path = os.path.join(DB_BACKUP_DIR, db_file)

        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل بکاپ دیتابیس \nFile: {db_file}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        cleanup_old_backups(DB_BACKUP_DIR)
        await show_main_menu(user_id, context)


    # ---------------- بکاپ مدیا ----------------
    elif data == "backup_media":
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
        media_file = latest_file(MEDIA_BACKUP_DIR, extension=".tar.gz")
        file_path = os.path.join(MEDIA_BACKUP_DIR, media_file)

        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        cleanup_old_backups(MEDIA_BACKUP_DIR)
        await show_main_menu(user_id, context)


    # ---------------- لیست بکاپ‌ها ----------------
    elif data == "list_backups":
        if not os.path.exists(DB_BACKUP_DIR):
            os.makedirs(DB_BACKUP_DIR)
        if not os.path.exists(MEDIA_BACKUP_DIR):
            os.makedirs(MEDIA_BACKUP_DIR)
        files = []
        # اضافه کردن بکاپ‌های دیتابیس
        files.extend([f"db:{f}" for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".sql")])
        # اضافه کردن بکاپ‌های مدیا
        files.extend([f"media:{f}" for f in os.listdir(MEDIA_BACKUP_DIR) if f.endswith(".tar.gz")])
        files = sorted(files, key=lambda x: get_file_datetime(x.split(":", 1)[1]), reverse=True)
        if not files:
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "در حال حاضر هیچ بکاپی از فایل دیتابیس و فولدر مدیا در لیست موجود نمی باشد ",
                reply_markup=reply_markup
            )
            return

        keyboard = []
        for f in files:
            file_type, filename = f.split(":", 1)
            file_datetime = get_file_datetime(filename)
            keyboard.append([
                InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy:{filename}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}")
            ])
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 بخش بکاپ‌ها\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "با کلیک روی دکمه (حذف) :\n"
            "بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n"
            "💡 برای کپی نام فایل، روی نام آن کلیک کنید.",
            reply_markup=reply_markup
        )

     # ---------------- کپی نام فایل ----------------
     
    elif data.startswith("copy:"):
        filename = data.split(":", 1)[1]
        await context.bot.answer_callback_query(
            callback_query_id=query.id, 
            text=f"✅ نام فایل {filename} آماده کپی شد!", 
            show_alert=True
        )
        await context.bot.send_message(chat_id=user_id, text=f"نام فایل برای کپی: `{filename}`", parse_mode="Markdown")
        

    # ---------------- حذف ----------------
    elif data.startswith("delete:"):
        _, file_type, filename = data.split(":", 2)
        backup_dir = DB_BACKUP_DIR if file_type == "db" else MEDIA_BACKUP_DIR
        file_path = os.path.join(backup_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} حذف شد.")
        
        # بازسازی لیست بکاپ‌ها بعد از حذف
        files = []
        files.extend([f"db:{f}" for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".sql")])
        files.extend([f"media:{f}" for f in os.listdir(MEDIA_BACKUP_DIR) if f.endswith(".tar.gz")])
        files = sorted(files, key=lambda x: get_file_datetime(x.split(":", 1)[1]), reverse=True)

        keyboard = []
        if files:
            for f in files:
                file_type, filename = f.split(":", 1)
                file_datetime = get_file_datetime(filename)
                keyboard.append([
                    InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"select:{f}"),
                    InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}")
                ])
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 بخش بکاپ‌ها\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "با کلیک روی دکمه (حذف) :\n"
            "بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n",
            reply_markup=reply_markup
        )
        
        
        
    # ---------------- منوی ریستور بکاپ ----------------
    elif data == "restore_backup":
        text = (
            "📥 منوی ریستور بکاپ\n\n"
            "در این بخش می‌توانید فایل‌های بکاپ دیتابیس یا مدیا را به نسخه فعلی بازگردانید.\n"
            "لطفاً دقت داشته باشید که ریستور بکاپ باعث جایگزینی فایل‌های موجود می‌شود!"
        )
        keyboard = [
            [InlineKeyboardButton("ریستور فولدر مدیا", callback_data="restore_media")],
            [InlineKeyboardButton("ریستور دیتابیس", callback_data="restore_db")],
            [InlineKeyboardButton("بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
        
        
            

    # ---------------- توضیحات بکاپ‌گیری ----------------
    elif data == "backup_info":
        text = f"""
📝 توضیحات بکاپ‌گیری روزانه

از طریق این ربات می‌توانید به‌صورت روزانه از وب‌سایت و اسکریپت هتلی خود بکاپ تهیه کنید.

01 - بکاپ دیتابیس : شامل تمام داده‌های پایگاه داده Safarname24 در قالب فایل (Sql)

02 - بکاپ مدیا : شامل تمامی فایل‌های مدیا در قالب فایل فشرده (tar.gz)

03 - تعداد بکاپ‌ها : حداکثر {MAX_BACKUPS} بکاپ اخیر نگهداری شده و نسخه‌های قدیمی به‌صورت خودکار حذف می‌شوند.

04 - حذف بکاپ : امکان حذف بکاپ‌های موجود.
    
    """

        keyboard = [
            [InlineKeyboardButton("🚀 ارتقا تعداد درخواست‌ها", callback_data="upgrade_requests")],
            [InlineKeyboardButton(" بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "upgrade_requests":
        await query.edit_message_text(
            "ویژگی ارتقای تعداد درخواست‌ها به‌ زودی در دسترس خواهد بود، برای جزئیات بیشتر می‌توانید با پشتیبانی در ارتباط باشید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" بازگشت", callback_data="backup_info")]])
        )

    # ---------------- بازگشت به منوی اصلی ----------------
    elif data == "go_back":
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)

    # ---------------- پشتیبانی ----------------
    elif data == "support":
        keyboard = [
            [InlineKeyboardButton(" 📮 تماس با پشتیبانی", url="https://t.me/sevintmadmin")],
            [InlineKeyboardButton(" بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("ادمین عزیز، در صورت بروز هرگونه مشکل در استفاده از ربات، می‌توانید از ساعت (9 صبح تا 21 شب) با کارشناس پشتیبانی ما در تلگرام در ارتباط باشید.", reply_markup=reply_markup)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()