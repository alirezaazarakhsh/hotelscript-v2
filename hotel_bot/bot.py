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
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/sf24_9xkLp7/")




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
    
-  امکانات ورژن 1.1 ربات
- 📦 بکاپ گیری دستی از دیتابیس و پوشه مدیا \n
- 🗂 نمایش لیست بکاپ ها با امکان حذف یا بازیابی (Restore) در سرور و دیتابیس \n
- 📮 پشتیبانی ارتباط سریع با ادمین \n
- 📋 راهنمای بکاپ گیری (در حال توسعه ...)\n
"""
    keyboard = [
        [InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"),
         InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")],
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
        text = "📦 انتخاب نوع بکاپ گیری \n\n💡 لازم به ذکر می باشد که می توانید از دیتابیس یا فولدر های مدیا بکاپ بگیرید "
        keyboard = [
            [InlineKeyboardButton(" 2 - دیتابیس", callback_data="backup_db"),
             InlineKeyboardButton(" 1 - فولدر مدیا", callback_data="backup_media")],
            [InlineKeyboardButton(" بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # ---------------- بکاپ دیتابیس ----------------
    elif data == "backup_db":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده سازی  بکاپ دیتابیس...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        db_file = f"db_{DATE}.sql"
        
        # استفاده از backup.sh برای گرفتن بکاپ دیتابیس
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        print(f"Running backup.sh for DB: {backup_script}")
        
        result = subprocess.run(f"{backup_script} db {db_file}", shell=True, capture_output=True, text=True)
        print(f"backup.sh stdout: {result.stdout}")
        print(f"backup.sh stderr: {result.stderr}")
        
        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ دیتابیس: {result.stderr}")
            return
        
        file_path = os.path.join(BACKUP_DIR, db_file)
        if os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ دیتابیس با موفقیت انجام شد.")
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل بکاپ دیتابیس \n  File : {db_file}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")
        
        cleanup_old_backups()
        await show_main_menu(user_id, context)





    # ---------------- بکاپ مدیا ----------------
    elif data == "backup_media":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده سازی بکاپ مدیا...")
        DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        media_file = f"media_{DATE}.tar.gz"
        result = subprocess.run(
            f"tar -czf {os.path.join(BACKUP_DIR, media_file)} -C {PROJECT_DIR} media",
            shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در گرفتن بکاپ مدیا: {result.stderr}")
            return

        file_path = os.path.join(BACKUP_DIR, media_file)
        if os.path.exists(file_path):
            # پیام موفقیت
            await context.bot.send_message(chat_id=user_id, text="✅ بکاپ مدیا با موفقیت انجام شد.")
            # پیام لینک دانلود
            media_url = MEDIA_BASE_URL + media_file
            await context.bot.send_message(chat_id=user_id, text=f"💾 لینک دانلود: {media_url}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        cleanup_old_backups()
        await show_main_menu(user_id, context)



    # ---------------- ادامه سایر بخش‌ها مثل قبل ----------------
    elif data == "list_backups":
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz") or f.endswith(".sql")], reverse=True)
        if not files:
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("در حال حاضر هیچ بکاپی از فایل دیتابیس و فولدر مدیا در لیست موجود نمی باشد ", reply_markup=reply_markup)
            return
        keyboard = []
        for f in files:
            file_datetime = get_file_datetime(f)
            keyboard.append([
                InlineKeyboardButton(f"{f} ({file_datetime})", callback_data=f"select:{f}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}")
            ])
            
            
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 بخش بکاپ‌ها\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "با کلیک روی دکمه (حذف) :\n"
            "بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n"
            "با کلیک روی دکمه (نام فایل) :\n"
            "به مرحله بعد رفته و بکاپ را بازیابی (Restore) کنید.",
            reply_markup=reply_markup
        )



    
     # ---------------- حذف و ریستور ----------------
     
    elif data.startswith("delete:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} حذف شد.")
        await button(update, context)  # بروزرسانی لیست بکاپ‌ها

    elif data.startswith("select:"):
        filename = data.split(":", 1)[1]
        keyboard = []
        if filename.endswith(".sql"):
            keyboard.append([InlineKeyboardButton("ریستور دیتابیس", callback_data=f"restore_db:{filename}")])
            text = (
                "انتخاب عملیات برای فایل زیر، در صورت تایید دکمه (ریستور دیتابیس) را انتخاب نمایید.\n\n"
                f"File : {filename}"
            )
        elif filename.endswith(".tar.gz"):
            keyboard.append([InlineKeyboardButton("ریستور مدیا", callback_data=f"restore_media:{filename}")])
            text = (
                "انتخاب عملیات برای فایل زیر، در صورت تایید دکمه (ریستور مدیا) را انتخاب نمایید.\n\n"
                f"File : {filename}"
            )
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif data.startswith("restore_db:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")
            return

        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏳ در حال پیاده سازی ریستور دیتابیس...\n\nFile : {filename}"
        )

        result = subprocess.run(
            f"{PROJECT_DIR}/restore.sh {file_path} dummy_media",
            shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "💢 خطایی رخ داد!\n"
                    "متأسفانه در عملیات ریستور دیتابیس مشکل سیستمی در ربات اتفاق افتاده است، "
                    "لطفاً مجدد تلاش نمایید."
                )
            )
            return

        await context.bot.send_message(chat_id=user_id, text=f"✅ ریستور دیتابیس با موفقیت انجام شد: {filename}")
        await show_main_menu(user_id, context)

    elif data.startswith("restore_media:"):
        filename = data.split(":", 1)[1]
        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            await context.bot.send_message(chat_id=user_id, text="❌ فایل پیدا نشد!")
            return

        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏳ در حال پیاده سازی ریستور مدیا...\n\nFile : {filename}"
        )

        result = subprocess.run(
            f"{PROJECT_DIR}/restore.sh dummy_db {file_path}",
            shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "💢 خطایی رخ داد!\n"
                    "متأسفانه در عملیات ریستور مدیا مشکل سیستمی در ربات اتفاق افتاده است، "
                    "لطفاً مجدد تلاش نمایید."
                )
            )
            return

        await context.bot.send_message(chat_id=user_id, text=f"✅ ریستور مدیا با موفقیت انجام شد: {filename}")
        await show_main_menu(user_id, context)





    # ---------------- توضیحات بکاپ‌گیری ----------------
    elif data == "backup_info":
        text = f"""
📝 توضیحات بکاپ‌گیری روزانه

از طریق این ربات می‌توانید به‌صورت روزانه از وب‌سایت و اسکریپت هتلی خود بکاپ تهیه کنید.

01 - بکاپ دیتابیس : شامل تمام داده‌های پایگاه داده Safarname24 در قالب فایل (Sql)

02 - بکاپ مدیا : شامل تمامی فایل‌های مدیا در قالب فایل فشرده (tar.gz)

03 - تعداد بکاپ‌ها : حداکثر {MAX_BACKUPS} بکاپ اخیر نگهداری شده و نسخه‌های قدیمی به‌صورت خودکار حذف می‌شوند.

04 - ریستور (Restore) : امکان بازگردانی دیتابیس یا فایل‌های مدیا از بکاپ‌های موجود.
    
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

