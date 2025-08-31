import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# ================= بارگذاری متغیرهای محیطی =================
load_dotenv(dotenv_path="hotel_bot/.env")  # مسیر فایل .env

PROJECT_DIR = os.getenv("PROJECT_DIR")
BACKUP_DIR = os.getenv("BACKUP_DIR")
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = list(map(int, os.getenv("ALLOWED_USERS").split(",")))
# ===========================================================

# بررسی دسترسی کاربر
def is_allowed(user_id):
    return user_id in ALLOWED_USERS

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📦 بکاپ جدید بگیر", callback_data="backup_now")],
        [InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("سلام! چه کاری میخوای انجام بدی؟", reply_markup=reply_markup)

# مدیریت دکمه‌ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not is_allowed(user_id):
        await query.edit_message_text("❌ شما اجازه دسترسی به این ربات را ندارید.")
        return

    # بکاپ جدید
    if query.data == "backup_now":
        await query.edit_message_text("⏳ در حال گرفتن بکاپ...")
        result = subprocess.run([f"{PROJECT_DIR}/backup.sh"], shell=True, capture_output=True, text=True)
        await query.edit_message_text(f"✅ بکاپ گرفته شد:\n{result.stdout or result.stderr}")

    # لیست بکاپ‌ها
    elif query.data == "list_backups":
        files = sorted(os.listdir(BACKUP_DIR), reverse=True)
        if not files:
            await query.edit_message_text("هیچ بکاپی موجود نیست.")
            return

        keyboard = []
        for f in files:
            keyboard.append([InlineKeyboardButton(f, callback_data=f"restore:{f}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 بکاپ‌ها:", reply_markup=reply_markup)

    # ریستور بکاپ
    elif query.data.startswith("restore:"):
        filename = query.data.split(":", 1)[1]

        if filename.endswith(".sql"):
            db_file = filename
            media_file = filename.replace("db_", "media_").replace(".sql", ".tar.gz")
            db_path = os.path.join(BACKUP_DIR, db_file)
            media_path = os.path.join(BACKUP_DIR, media_file)

            if not os.path.exists(media_path):
                await query.edit_message_text("❌ فایل مدیا پیدا نشد!")
                return

            await query.edit_message_text(f"⏳ در حال ریستور بکاپ {db_file} ...")
            cmd = f"{PROJECT_DIR}/restore.sh {db_path} {media_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            await query.edit_message_text(f"🔄 ریستور انجام شد:\n{result.stdout or result.stderr}")

# Main
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")
app.run_polling()
