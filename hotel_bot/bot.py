import os
import subprocess
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

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
SUPER_ADMINS = list(map(int, os.getenv("SUPER_ADMINS", "").split(",")))  # سوپر ادمین‌ها از .env
MAX_BACKUPS = 7
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/sf24_9xkLp7/")

ADMINS_FILE = "admins.json"  # فایل برای ذخیره ادمین‌ها و گروه‌ها

# ===========================================================

# مجوزهای موجود
PERMISSIONS = [
    'backup_db',
    'backup_media',
    'list_backups',
    'delete_backups',
    'restore_db',
    'restore_media',
    'backup_info',
    'support',
    'manage_admins'  # مجوز مدیریت ادمین‌ها و گروه‌ها
]

def load_data():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r') as f:
            data = json.load(f)
            # تبدیل به set برای مجوزها
            for uid in data.get('admins', {}):
                data['admins'][uid] = set(data['admins'][uid])
            for gname in data.get('groups', {}):
                data['groups'][gname] = set(data['groups'][gname])
            return data
    return {'admins': {}, 'groups': {}}

def save_data(data):
    # تبدیل set به list برای json
    saveable = {
        'admins': {uid: list(perms) for uid, perms in data['admins'].items()},
        'groups': {gname: list(perms) for gname, perms in data['groups'].items()}
    }
    with open(ADMINS_FILE, 'w') as f:
        json.dump(saveable, f)

data = load_data()
admins = data['admins']
groups = data['groups']

def is_allowed(user_id, permission=None):
    if user_id in SUPER_ADMINS:
        return True
    if user_id not in admins:
        return False
    if permission is None:
        return bool(admins[user_id])  # اگر حداقل یک مجوز داشته باشه
    return permission in admins[user_id]

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
        [InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu") if is_allowed(user_id, 'backup_db') or is_allowed(user_id, 'backup_media') else None,
         InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups") if is_allowed(user_id, 'list_backups') else None],
        [InlineKeyboardButton("🗃 ریستور بکاپ", callback_data="restore_backup") if is_allowed(user_id, 'restore_db') or is_allowed(user_id, 'restore_media') else None],
        [InlineKeyboardButton("📋 نحوه بکاپ‌گیری", callback_data="backup_info") if is_allowed(user_id, 'backup_info') else None,
         InlineKeyboardButton("📮 پشتیبانی", callback_data="support") if is_allowed(user_id, 'support') else None]
    ]
    if is_allowed(user_id, 'manage_admins'):
        keyboard.append([InlineKeyboardButton("⚙️ کنترل پنل", callback_data="control_panel")])
    
    # فیلتر ردیف‌های خالی
    keyboard = [row for row in keyboard if any(row)]
    
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

# ======================== مدیریت پیام‌ها (برای ورودی ID و نام گروه) ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id, 'manage_admins'):
        return

    state = context.user_data.get('state')
    text = update.message.text

    if state == 'waiting_for_admin_id':
        try:
            new_id = int(text)
            if new_id in admins or new_id in SUPER_ADMINS:
                await update.message.reply_text("این کاربر قبلاً ادمین است!")
                return
            context.user_data['new_admin_id'] = new_id
            context.user_data['selected_perms'] = set()
            context.user_data['state'] = 'select_permissions'
            await show_permissions_selection(update.message.chat_id, context, new_id)
        except ValueError:
            await update.message.reply_text("لطفاً یک ID عددی معتبر وارد کنید.")

    elif state == 'waiting_for_group_name':
        group_name = text.strip()
        if group_name in groups:
            await update.message.reply_text("این گروه قبلاً وجود دارد!")
            return
        context.user_data['new_group_name'] = group_name
        context.user_data['selected_perms'] = set()
        context.user_data['state'] = 'select_group_permissions'
        await show_permissions_selection(update.message.chat_id, context, group_name, is_group=True)

# ======================== نمایش انتخاب مجوزها ========================
async def show_permissions_selection(chat_id, context, target, is_group=False, message_id=None):
    selected = context.user_data.get('selected_perms', set())
    keyboard = []
    for perm in PERMISSIONS:
        label = f"{'✅ ' if perm in selected else ''}{perm}"
        callback = f"toggle_perm:{perm}:{'group' if is_group else 'admin'}"
        keyboard.append([InlineKeyboardButton(label, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("تأیید", callback_data=f"confirm_perms:{'group' if is_group else 'admin'}")])
    keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_perms")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"انتخاب مجوزها برای {'گروه: ' + target if is_group else 'ادمین ID: ' + str(target)}"
    
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

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

    # ---------------- چک مجوز برای اقدامات ----------------
    if data == "backup_menu" and not (is_allowed(user_id, 'backup_db') or is_allowed(user_id, 'backup_media')):
        return
    if data == "backup_db" and not is_allowed(user_id, 'backup_db'):
        return
    if data == "backup_media" and not is_allowed(user_id, 'backup_media'):
        return
    if data == "list_backups" and not is_allowed(user_id, 'list_backups'):
        return
    if data.startswith("delete:") and not is_allowed(user_id, 'delete_backups'):
        return
    if data == "restore_backup" and not (is_allowed(user_id, 'restore_db') or is_allowed(user_id, 'restore_media')):
        return
    if data == "backup_info" and not is_allowed(user_id, 'backup_info'):
        return
    if data == "support" and not is_allowed(user_id, 'support'):
        return

    # ---------------- منوی بکاپ ----------------
    if data == "backup_menu":
        text = "📦 انتخاب نوع بکاپ گیری \n\nلازم به ذکر می باشد که می توانید از دیتابیس یا فولدر های مدیا بکاپ بگیرید "
        keyboard = [
            [InlineKeyboardButton(" 2 - دیتابیس", callback_data="backup_db") if is_allowed(user_id, 'backup_db') else None,
             InlineKeyboardButton(" 1 - فولدر مدیا", callback_data="backup_media") if is_allowed(user_id, 'backup_media') else None],
            [InlineKeyboardButton(" بازگشت", callback_data="go_back")]
        ]
        keyboard = [row for row in keyboard if any(row)]
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
                "در حال حاضر هیچ بکاپی از فایل دیتابیس و فولدر مدیا در لیست موجود نمی باشد",
                reply_markup=reply_markup
            )
            return

        keyboard = []
        for f in files:
            file_type, filename = f.split(":", 1)
            file_datetime = get_file_datetime(filename)
            keyboard.append([
                # دکمه‌ای که نام فایل را برای کپی کردن نمایش می‌دهد
                InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", 
                                    callback_data=f"copy_name:{filename}"),
                # دکمه حذف اگر مجوز داشته باشه
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}") if is_allowed(user_id, 'delete_backups') else None
            ])

        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]  # فیلتر خالی‌ها
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 بخش بکاپ‌ها\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "با کلیک روی دکمه (حذف) :\n"
            "بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n"
            "با کلیک روی اسم فایل :\n"
            "نام فایل برای شما نمایش داده می‌شود تا بتوانید آن را کپی کنید.",
            reply_markup=reply_markup
        )

    # ---------------- هندلر کلیک روی دکمه کپی ----------------
    elif data.startswith("copy_name:"):
        filename = data.split(":", 1)[1]
        # نمایش پاپ‌آپ با نام فایل
        await query.answer(f"نام فایل: {filename}", show_alert=True)

    # ---------------- حذف ----------------
    elif data.startswith("delete:"):
        f = data.split(":", 1)[1]
        file_type, filename = f.split(":", 1)
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
                    InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy_name:{filename}"),
                    InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{f}") if is_allowed(user_id, 'delete_backups') else None
                ])
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]
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
            [InlineKeyboardButton("ریستور فولدر مدیا", callback_data="restore_media") if is_allowed(user_id, 'restore_media') else None],
            [InlineKeyboardButton("ریستور دیتابیس", callback_data="restore_db") if is_allowed(user_id, 'restore_db') else None],
            [InlineKeyboardButton("بازگشت", callback_data="go_back")]
        ]
        keyboard = [row for row in keyboard if any(row)]
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

    # ---------------- کنترل پنل ----------------
    elif data == "control_panel":
        if not is_allowed(user_id, 'manage_admins'):
            return
        text = "⚙️ کنترل پنل ربات"
        keyboard = [
            [InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin")],
            [InlineKeyboardButton("👥 ایجاد گروه دسترسی", callback_data="create_group")],
            [InlineKeyboardButton("بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # ---------------- اضافه کردن ادمین ----------------
    elif data == "add_admin":
        if not is_allowed(user_id, 'manage_admins'):
            return
        context.user_data['state'] = 'waiting_for_admin_id'
        await context.bot.send_message(chat_id=chat_id, text="لطفاً ID عددی کاربر را ارسال کنید.")

    # ---------------- ایجاد گروه ----------------
    elif data == "create_group":
        if not is_allowed(user_id, 'manage_admins'):
            return
        context.user_data['state'] = 'waiting_for_group_name'
        await context.bot.send_message(chat_id=chat_id, text="لطفاً نام گروه دسترسی را ارسال کنید.")

    # ---------------- toggle مجوز ----------------
    elif data.startswith("toggle_perm:"):
        if not is_allowed(user_id, 'manage_admins'):
            return
        _, perm, target_type = data.split(":", 2)
        selected = context.user_data.get('selected_perms', set())
        if perm in selected:
            selected.remove(perm)
        else:
            selected.add(perm)
        context.user_data['selected_perms'] = selected
        target = context.user_data['new_group_name'] if target_type == 'group' else context.user_data['new_admin_id']
        await show_permissions_selection(chat_id, context, target, is_group=(target_type == 'group'), message_id=message_id)

    # ---------------- تأیید مجوزها ----------------
    elif data.startswith("confirm_perms:"):
        if not is_allowed(user_id, 'manage_admins'):
            return
        target_type = data.split(":", 1)[1]
        selected = context.user_data.get('selected_perms', set())
        if target_type == 'admin':
            new_id = context.user_data.get('new_admin_id')
            if new_id:
                admins[new_id] = selected
                save_data(data)
                await query.edit_message_text("✅ ادمین با موفقیت اضافه شد.")
        elif target_type == 'group':
            group_name = context.user_data.get('new_group_name')
            if group_name:
                groups[group_name] = selected
                save_data(data)
                await query.edit_message_text("✅ گروه دسترسی با موفقیت ایجاد شد.")
        context.user_data.clear()
        await show_main_menu(user_id, context)

    # ---------------- لغو ----------------
    elif data == "cancel_perms":
        context.user_data.clear()
        await query.edit_message_text("عملیات لغو شد.")
        await show_main_menu(user_id, context)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling()