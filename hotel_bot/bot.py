import os
import subprocess
import json
from datetime import datetime
from dotenv import load_dotenv
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
# مدیریت SUPER_ADMINS برای جلوگیری از خطا در صورت خالی بودن
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x]
MAX_BACKUPS = 7
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/sf24_9xkLp7/")

ADMINS_FILE = "admins.json"  # فایل برای ذخیره ادمین‌ها و گروه‌ها

# ===========================================================

# مجوزهای موجود (انگلیسی برای کد، اما نمایش فارسی)
PERMISSIONS = [
    'backup_db',
    'backup_media',
    'list_backups',
    'delete_backups',
    'restore_db',
    'restore_media',
    'backup_info',
    'support',
    'manage_admins'
]

# نمایش فارسی مجوزها با توضیحات
PERM_DISPLAY = {
    'backup_db': {'label': 'بکاپ دیتابیس', 'desc': 'اجازه بکاپ‌گیری از پایگاه داده (فایل SQL). این گزینه برای حفظ داده‌های اصلی سایت ضروری است.'},
    'backup_media': {'label': 'بکاپ مدیا', 'desc': 'اجازه بکاپ‌گیری از فایل‌های رسانه‌ای (فشرده tar.gz). شامل تصاویر، ویدیوها و سایر فایل‌های آپلود شده.'},
    'list_backups': {'label': 'لیست بکاپ‌ها', 'desc': 'نمایش لیست بکاپ‌های موجود. مفید برای بررسی تاریخچه بکاپ‌ها.'},
    'delete_backups': {'label': 'حذف بکاپ‌ها', 'desc': 'حذف بکاپ‌های قدیمی یا غیرضروری. توجه: این عمل برگشت‌ناپذیر است.'},
    'restore_db': {'label': 'ریستور دیتابیس', 'desc': 'بازگردانی بکاپ دیتابیس به وضعیت فعلی. ممکن است داده‌های فعلی را جایگزین کند.'},
    'restore_media': {'label': 'ریستور مدیا', 'desc': 'بازگردانی بکاپ فایل‌های رسانه‌ای. ممکن است فایل‌های فعلی را جایگزین کند.'},
    'backup_info': {'label': 'اطلاعات بکاپ', 'desc': 'نمایش راهنما و توضیحات در مورد فرآیند بکاپ‌گیری.'},
    'support': {'label': 'پشتیبانی', 'desc': 'دسترسی به بخش پشتیبانی و تماس با ادمین.'},
    'manage_admins': {'label': 'مدیریت ادمین‌ها', 'desc': 'مدیریت کاربران ادمین و گروه‌های دسترسی. فقط برای سوپرادمین‌ها.'}
}

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
    str_uid = str(user_id)
    if str_uid not in admins:
        return False
    if permission is None:
        return bool(admins[str_uid])  # اگر حداقل یک مجوز داشته باشه
    return permission in admins[str_uid]

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
سلام {username}!
به ربات اسکریپت هتل خوش اومدی 👋🏻

در این نسخه از ربات تلاش کرده‌ایم تمامی نیازهای شما را پوشش دهیم و مدیریت اسکریپت را آسان کنیم.

**امکانات ورژن 1.1 ربات:**

📦 **بکاپ‌گیری دستی** از دیتابیس و پوشه مدیا
🗂 **نمایش لیست بکاپ‌ها** با امکان حذف
📮 **پشتیبانی** ارتباط سریع با ادمین
📋 **راهنمای بکاپ‌گیری** (در حال توسعه...)
"""
    keyboard = []
    row = []
    if is_allowed(user_id, 'backup_db') or is_allowed(user_id, 'backup_media'):
        row.append(InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"))
    if is_allowed(user_id, 'list_backups'):
        row.append(InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups"))
    if row:
        keyboard.append(row)
    row = []
    if is_allowed(user_id, 'restore_db') or is_allowed(user_id, 'restore_media'):
        row.append(InlineKeyboardButton("🗃 ریستور بکاپ", callback_data="restore_backup"))
    if is_allowed(user_id, 'backup_info'):
        row.append(InlineKeyboardButton("📋 نحوه بکاپ‌گیری", callback_data="backup_info"))
    if row:
        keyboard.append(row)
    row = []
    if is_allowed(user_id, 'support'):
        row.append(InlineKeyboardButton("📮 پشتیبانی", callback_data="support"))
    if is_allowed(user_id, 'manage_admins'):
        row.append(InlineKeyboardButton("⚙️ کنترل پنل", callback_data="control_panel"))
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id and chat_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

# ======================== نمایش لیست ادمین‌ها ========================
async def show_manage_admins(chat_id, context, message_id=None):
    if not admins:
        text = "هیچ ادمینی وجود ندارد.\n\nتوضیح: می‌توانید ادمین‌های جدید اضافه کنید یا گروه‌های دسترسی را مدیریت کنید."
        keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
    else:
        text = "لیست ادمین‌ها:\n\nتوضیح: می‌توانید هر ادمین را ویرایش یا حذف کنید."
        keyboard = []
        row = []
        for idx, uid in enumerate(admins):
            row.append(InlineKeyboardButton(f"ID: {uid}", callback_data=f"view_admin:{uid}"))
            if (idx + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

# ======================== نمایش جزئیات ادمین ========================
async def show_admin_details(chat_id, context, admin_id, message_id=None):
    perms = admins.get(admin_id, set())
    text = f"جزئیات ادمین ID: {admin_id}\n\nمجوزها:\n"
    for perm in perms:
        text += f"- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}\n"
    if not perms:
        text += "هیچ مجوزی اختصاص نیافته.\n"
    text += "\nتوضیح: می‌توانید گروه دسترسی یا مجوزهای این ادمین را ویرایش کنید یا ادمین را حذف کنید."
    
    keyboard = [
        [InlineKeyboardButton("اختصاص گروه دسترسی", callback_data=f"assign_group_menu:{admin_id}"),
         InlineKeyboardButton("ویرایش مجوزها", callback_data=f"edit_admin_perms:{admin_id}")],
        [InlineKeyboardButton("حذف ادمین", callback_data=f"delete_admin:{admin_id}"),
         InlineKeyboardButton("بازگشت", callback_data="manage_admins")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

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
        await update.message.reply_text("❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
        return

    state = context.user_data.get('state')
    text = update.message.text

    if state == 'waiting_for_admin_id':
        try:
            new_id = int(text)
            if str(new_id) in admins or new_id in SUPER_ADMINS:
                await update.message.reply_text("❌ این کاربر قبلاً ادمین است!")
                return
            context.user_data['new_admin_id'] = new_id
            await show_group_selection(update.message.chat_id, context, new_id)
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک ID عددی معتبر وارد کنید.")

    elif state == 'waiting_for_group_name':
        group_name = text.strip()
        if group_name in groups:
            await update.message.reply_text("❌ این گروه قبلاً وجود دارد!")
            return
        context.user_data['new_group_name'] = group_name
        context.user_data['selected_perms'] = set()
        context.user_data['state'] = 'select_group_permissions'
        await show_permissions_selection(update.message.chat_id, context, group_name, is_group=True)

    elif state == 'waiting_for_new_group_name':
        new_name = text.strip()
        old_name = context.user_data.get('editing_group')
        if new_name != old_name and new_name in groups:
            await update.message.reply_text("❌ این نام گروه قبلاً وجود دارد!")
            return
        groups[new_name] = groups.pop(old_name)
        save_data(data)
        await update.message.reply_text(f"✅ نام گروه به {new_name} تغییر یافت.")
        context.user_data.clear()
        await show_manage_groups(update.message.chat_id, context)

# ======================== نمایش انتخاب گروه برای ادمین ========================
async def show_group_selection(chat_id, context, admin_id, message_id=None):
    if not groups:
        text = "هیچ گروه دسترسی‌ای وجود ندارد. ابتدا یک گروه ایجاد کنید.\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که می‌توانید مجوزها را به آن‌ها اختصاص دهید و سپس به ادمین‌ها割り دهید."
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="control_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return
    text = f"انتخاب گروه دسترسی برای ادمین ID: {admin_id}\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که مجوزهای از پیش تعریف‌شده دارند. با انتخاب یک گروه، مجوزهای آن به ادمین اختصاص می‌یابد."
    keyboard = []
    row = []
    for idx, gname in enumerate(groups):
        row.append(InlineKeyboardButton(gname, callback_data=f"assign_group:{gname}:{admin_id}"))
        if (idx + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_perms")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

# ======================== نمایش انتخاب مجوزها ========================
async def show_permissions_selection(chat_id, context, target, is_group=False, message_id=None, show_desc=False):
    selected = context.user_data.get('selected_perms', set())
    text = f"انتخاب مجوزها برای {'گروه: ' + target if is_group else 'ادمین ID: ' + str(target)}\n\nتوضیح: مجوزها دسترسی‌های خاصی را تعریف می‌کنند. می‌توانید چندین مجوز را انتخاب کنید. برای هر مجوز توضیح مختصری وجود دارد."
    if show_desc:
        for perm in PERMISSIONS:
            text += f"\n- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}"
    
    keyboard = []
    row = []
    for idx, perm in enumerate(PERMISSIONS):
        label = f"{'✅ ' if perm in selected else ''}{PERM_DISPLAY[perm]['label']}"
        callback = f"toggle_perm:{perm}:{'group' if is_group else 'admin'}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if (idx + 1) % 2 == 0:  # کنار هم (2 در ردیف)
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("تأیید", callback_data=f"confirm_perms:{'group' if is_group else 'admin'}")])
    keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_perms")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

# ======================== نمایش مدیریت گروه‌ها ========================
async def show_manage_groups(chat_id, context, message_id=None):
    if not groups:
        text = "هیچ گروه دسترسی‌ای وجود ندارد.\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که می‌توانید مجوزها را به آن‌ها اختصاص دهید و سپس به ادمین‌ها割り دهید."
        keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
    else:
        text = "لیست گروه‌های دسترسی:\n\nتوضیح: می‌توانید هر گروه را ویرایش، حذف یا مجوزهای آن را مشاهده کنید."
        keyboard = []
        row = []
        for idx, gname in enumerate(groups):
            row.append(InlineKeyboardButton(gname, callback_data=f"view_group:{gname}"))
            if (idx + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if message_id:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

# ======================== نمایش جزئیات گروه ========================
async def show_group_details(chat_id, context, group_name, message_id=None):
    perms = groups.get(group_name, set())
    text = f"جزئیات گروه: {group_name}\n\nمجوزها:\n"
    for perm in perms:
        text += f"- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}\n"
    if not perms:
        text += "هیچ مجوزی اختصاص نیافته.\n"
    text += "\nتوضیح: می‌توانید مجوزها را ویرایش کنید، نام گروه را تغییر دهید یا گروه را حذف کنید."
    
    keyboard = [
        [InlineKeyboardButton("ویرایش مجوزها", callback_data=f"edit_group_perms:{group_name}"),
         InlineKeyboardButton("تغییر نام", callback_data=f"rename_group:{group_name}")],
        [InlineKeyboardButton("حذف گروه", callback_data=f"delete_group:{group_name}"),
         InlineKeyboardButton("بازگشت", callback_data="manage_groups")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
        await query.edit_message_text("❌ شما مجوز دسترسی به منوی بکاپ‌گیری را ندارید!")
        return
    if data == "backup_db" and not is_allowed(user_id, 'backup_db'):
        await query.edit_message_text("❌ شما مجوز بکاپ‌گیری از دیتابیس را ندارید!")
        return
    if data == "backup_media" and not is_allowed(user_id, 'backup_media'):
        await query.edit_message_text("❌ شما مجوز بکاپ‌گیری از مدیا را ندارید!")
        return
    if data == "list_backups" and not is_allowed(user_id, 'list_backups'):
        await query.edit_message_text("❌ شما مجوز مشاهده لیست بکاپ‌ها را ندارید!")
        return
    if data.startswith("delete:") and not is_allowed(user_id, 'delete_backups'):
        await query.edit_message_text("❌ شما مجوز حذف بکاپ‌ها را ندارید!")
        return
    if data == "restore_backup" and not (is_allowed(user_id, 'restore_db') or is_allowed(user_id, 'restore_media')):
        await query.edit_message_text("❌ شما مجوز ریستور بکاپ را ندارید!")
        return
    if data == "backup_info" and not is_allowed(user_id, 'backup_info'):
        await query.edit_message_text("❌ شما مجوز مشاهده اطلاعات بکاپ را ندارید!")
        return
    if data == "support" and not is_allowed(user_id, 'support'):
        await query.edit_message_text("❌ شما مجوز دسترسی به پشتیبانی را ندارید!")
        return

    # ---------------- منوی بکاپ ----------------
    if data == "backup_menu":
        text = "📦 **انتخاب نوع بکاپ‌گیری**\n\nلازم به ذکر است که می‌توانید از دیتابیس یا فولدرهای مدیا بکاپ بگیرید.\n\n**توضیح**: بکاپ دیتابیس داده‌های سایت را حفظ می‌کند، بکاپ مدیا فایل‌های آپلود شده را."
        keyboard = [[
            InlineKeyboardButton("دیتابیس", callback_data="backup_db") if is_allowed(user_id, 'backup_db') else None,
            InlineKeyboardButton("فولدر مدیا", callback_data="backup_media") if is_allowed(user_id, 'backup_media') else None
        ]]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    # ---------------- بکاپ دیتابیس ----------------
    elif data == "backup_db":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ دیتابیس...")
        
        # اجرای backup.sh
        backup_script = os.path.join(PROJECT_DIR, "backup.sh")
        if not os.path.exists(DB_BACKUP_DIR):
            os.makedirs(DB_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ دیتابیس ایجاد شد.")

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
            await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=f"فایل بکاپ دیتابیس\nFile: {db_file}")
        else:
            await context.bot.send_message(chat_id=user_id, text="❌ فایل بکاپ پیدا نشد!")

        cleanup_old_backups(DB_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="✅ بکاپ‌های قدیمی با موفقیت مدیریت شدند.")
        await show_main_menu(user_id, context)

    # ---------------- بکاپ مدیا ----------------
    elif data == "backup_media":
        await context.bot.send_message(chat_id=user_id, text="⏳ در حال پیاده‌سازی بکاپ مدیا...")

        if not os.path.exists(MEDIA_BACKUP_DIR):
            os.makedirs(MEDIA_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ مدیا ایجاد شد.")

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
        await context.bot.send_message(chat_id=user_id, text="✅ بکاپ‌های قدیمی با موفقیت مدیریت شدند.")
        await show_main_menu(user_id, context)

    # ---------------- لیست بکاپ‌ها ----------------
    elif data == "list_backups":
        if not os.path.exists(DB_BACKUP_DIR):
            os.makedirs(DB_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ دیتابیس ایجاد شد.")
        if not os.path.exists(MEDIA_BACKUP_DIR):
            os.makedirs(MEDIA_BACKUP_DIR)
            await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ مدیا ایجاد شد.")

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
                "در حال حاضر هیچ بکاپی از فایل دیتابیس و فولدر مدیا در لیست موجود نیست.\n\n**توضیح**: ابتدا بکاپی ایجاد کنید تا در این بخش نمایش داده شود.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        keyboard = []
        for f in files:
            file_type, filename = f.split(":", 1)
            file_datetime = get_file_datetime(filename)
            row = [
                InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", 
                                    callback_data=f"copy_name:{filename}"),
            ]
            if is_allowed(user_id, 'delete_backups'):
                row.append(InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}"))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 **بخش بکاپ‌ها**\n\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "**با کلیک روی دکمه (حذف):** بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n"
            "**با کلیک روی اسم فایل:** نام فایل برای شما نمایش داده می‌شود تا بتوانید آن را کپی کنید.\n\n"
            "**توضیح**: بکاپ‌ها به صورت خودکار قدیمی‌ترین‌ها را حذف می‌کنند تا فضای ذخیره‌سازی مدیریت شود.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    # ---------------- هندلر کلیک روی دکمه کپی ----------------
    elif data.startswith("copy_name:"):
        filename = data.split(":", 1)[1]
        # نمایش پاپ‌آپ با نام فایل
        await query.answer(f"نام فایل: {filename}", show_alert=True)

    # ---------------- حذف ----------------
    elif data.startswith("delete:"):
        _, file_type, filename = data.split(":", 2)
        backup_dir = DB_BACKUP_DIR if file_type == "db" else MEDIA_BACKUP_DIR
        file_path = os.path.join(backup_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} با موفقیت حذف شد.")
        else:
            await context.bot.send_message(chat_id=user_id, text=f"❌ فایل {filename} پیدا نشد!")
        
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
                row = [
                    InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy_name:{filename}"),
                ]
                if is_allowed(user_id, 'delete_backups'):
                    row.append(InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}"))
                keyboard.append(row)
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📁 **بخش بکاپ‌ها**\n\n"
            "در این بخش می‌توانید لیست 7 بکاپ آخر از دیتابیس و پوشه مدیا را مشاهده کنید.\n\n"
            "**با کلیک روی دکمه (حذف):** بکاپ فایل موردنظر را می‌توانید پاک کنید.\n\n"
            "**با کلیک روی اسم فایل:** نام فایل برای شما نمایش داده می‌شود تا بتوانید آن را کپی کنید.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    # ---------------- منوی ریستور بکاپ ----------------
    elif data == "restore_backup":
        text = (
            "📥 **منوی ریستور بکاپ**\n\n"
            "در این بخش می‌توانید فایل‌های بکاپ دیتابیس یا مدیا را به نسخه فعلی بازگردانید.\n"
            "**لطفاً دقت کنید:** ریستور بکاپ باعث جایگزینی فایل‌های موجود می‌شود!\n\n"
            "**توضیح**: قبل از ریستور، از وضعیت فعلی بکاپ بگیرید تا در صورت مشکل بتوانید بازگردانی کنید."
        )
        keyboard = [[
            InlineKeyboardButton("ریستور فولدر مدیا", callback_data="restore_media") if is_allowed(user_id, 'restore_media') else None,
            InlineKeyboardButton("ریستور دیتابیس", callback_data="restore_db") if is_allowed(user_id, 'restore_db') else None
        ]]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        
    # ---------------- توضیحات بکاپ‌گیری ----------------
    elif data == "backup_info":
        text = f"""
📝 **توضیحات بکاپ‌گیری روزانه**

از طریق این ربات می‌توانید به‌صورت روزانه از وب‌سایت و اسکریپت هتلی خود بکاپ تهیه کنید.

1️⃣ **بکاپ دیتابیس**: شامل تمام داده‌های پایگاه داده Safarname24 در قالب فایل (SQL). این بکاپ برای حفظ اطلاعات کاربران و تنظیمات ضروری است.

2️⃣ **بکاپ مدیا**: شامل تمامی فایل‌های مدیا در قالب فایل فشرده (tar.gz). شامل تصاویر هتل‌ها، ویدیوها و فایل‌های آپلود شده توسط کاربران.

3️⃣ **تعداد بکاپ‌ها**: حداکثر {MAX_BACKUPS} بکاپ اخیر نگهداری شده و نسخه‌های قدیمی به‌صورت خودکار حذف می‌شوند تا فضای ذخیره‌سازی بهینه باشد.

4️⃣ **حذف بکاپ**: امکان حذف بکاپ‌های موجود برای مدیریت فضای ذخیره.
        """
        keyboard = [
            [InlineKeyboardButton("🚀 ارتقا تعداد درخواست‌ها", callback_data="upgrade_requests")],
            [InlineKeyboardButton("بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "upgrade_requests":
        await query.edit_message_text(
            "ویژگی ارتقای تعداد درخواست‌ها به‌زودی در دسترس خواهد بود، برای جزئیات بیشتر می‌توانید با پشتیبانی در ارتباط باشید.\n\n**توضیح**: این ارتقا اجازه بکاپ‌های بیشتر یا ویژگی‌های پیشرفته را فراهم می‌کند.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="backup_info")]]),
            parse_mode="Markdown"
        )

    # ---------------- بازگشت به منوی اصلی ----------------
    elif data == "go_back":
        await show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)

    # ---------------- پشتیبانی ----------------
    elif data == "support":
        keyboard = [
            [InlineKeyboardButton("📮 تماس با پشتیبانی", url="https://t.me/sevintmadmin")],
            [InlineKeyboardButton("بازگشت", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "ادمین عزیز، در صورت بروز هرگونه مشکل در استفاده از ربات، می‌توانید از ساعت (9 صبح تا 21 شب) با کارشناس پشتیبانی ما در تلگرام در ارتباط باشید.\n\n**توضیح**: پشتیبانی برای حل مشکلات فنی، راهنمایی و پیشنهادات در دسترس است.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    # ---------------- کنترل پنل ----------------
    elif data == "control_panel":
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز دسترسی به کنترل پنل را ندارید!")
            return
        text = "⚙️ **کنترل پنل ربات**\n\n**توضیح**: در این بخش می‌توانید ادمین‌ها و گروه‌های دسترسی را مدیریت کنید."
        keyboard = [[
            InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin"),
            InlineKeyboardButton("👥 ایجاد گروه دسترسی", callback_data="create_group")
        ],[
            InlineKeyboardButton("🛠 مدیریت گروه‌های دسترسی", callback_data="manage_groups"),
            InlineKeyboardButton("👤 مدیریت ادمین‌ها", callback_data="manage_admins")
        ]]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    # ---------------- اضافه کردن ادمین ----------------
    elif data == "add_admin":
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز افزودن ادمین را ندارید!")
            return
        context.user_data['state'] = 'waiting_for_admin_id'
        await context.bot.send_message(
            chat_id=chat_id,
            text="لطفاً ID عددی کاربر را ارسال کنید.\n\n**توضیح**: ID کاربر را از تنظیمات تلگرام یا بات‌های دیگر می‌توانید پیدا کنید.",
            parse_mode="Markdown"
        )

    # ---------------- ایجاد گروه ----------------
    elif data == "create_group":
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ایجاد گروه دسترسی را ندارید!")
            return
        context.user_data['state'] = 'waiting_for_group_name'
        await context.bot.send_message(
            chat_id=chat_id,
            text="لطفاً نام گروه دسترسی را ارسال کنید.\n\n**توضیح**: نام گروه باید منحصر به فرد باشد و برای شناسایی نقش استفاده می‌شود.",
            parse_mode="Markdown"
        )

    # ---------------- مدیریت گروه‌ها ----------------
    elif data == "manage_groups":
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز مدیریت گروه‌های دسترسی را ندارید!")
            return
        await show_manage_groups(chat_id, context, message_id=message_id)

    # ---------------- مدیریت ادمین‌ها ----------------
    elif data == "manage_admins":
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
            return
        await show_manage_admins(chat_id, context, message_id=message_id)

    # ---------------- مشاهده گروه ----------------
    elif data.startswith("view_group:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز مشاهده گروه را ندارید!")
            return
        group_name = data.split(":", 1)[1]
        await show_group_details(chat_id, context, group_name, message_id=message_id)

    # ---------------- مشاهده ادمین ----------------
    elif data.startswith("view_admin:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز مشاهده ادمین را ندارید!")
            return
        admin_id = data.split(":", 1)[1]
        await show_admin_details(chat_id, context, admin_id, message_id=message_id)

    # ---------------- ویرایش مجوزهای گروه ----------------
    elif data.startswith("edit_group_perms:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش گروه را ندارید!")
            return
        group_name = data.split(":", 1)[1]
        context.user_data['editing_group'] = group_name
        context.user_data['selected_perms'] = groups.get(group_name, set())
        context.user_data['state'] = 'select_group_permissions'
        await show_permissions_selection(chat_id, context, group_name, is_group=True, message_id=message_id, show_desc=True)

    # ---------------- ویرایش مجوزهای ادمین ----------------
    elif data.startswith("edit_admin_perms:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش ادمین را ندارید!")
            return
        admin_id = data.split(":", 1)[1]
        context.user_data['editing_admin'] = admin_id
        context.user_data['selected_perms'] = admins.get(admin_id, set())
        context.user_data['state'] = 'select_admin_permissions'
        await show_permissions_selection(chat_id, context, admin_id, is_group=False, message_id=message_id, show_desc=True)

    # ---------------- تغییر نام گروه ----------------
    elif data.startswith("rename_group:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز تغییر نام گروه را ندارید!")
            return
        group_name = data.split(":", 1)[1]
        context.user_data['editing_group'] = group_name
        context.user_data['state'] = 'waiting_for_new_group_name'
        await context.bot.send_message(
            chat_id=chat_id,
            text="لطفاً نام جدید گروه را ارسال کنید.\n\n**توضیح**: نام جدید باید منحصر به فرد باشد.",
            parse_mode="Markdown"
        )

    # ---------------- حذف گروه ----------------
    elif data.startswith("delete_group:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز حذف گروه را ندارید!")
            return
        group_name = data.split(":", 1)[1]
        if group_name in groups:
            del groups[group_name]
            save_data(data)
            await query.edit_message_text("✅ گروه با موفقیت حذف شد.")
        else:
            await query.edit_message_text("❌ گروه یافت نشد!")
        await show_manage_groups(chat_id, context)

    # ---------------- حذف ادمین ----------------
    elif data.startswith("delete_admin:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز حذف ادمین را ندارید!")
            return
        admin_id = data.split(":", 1)[1]
        if admin_id in admins:
            del admins[admin_id]
            save_data(data)
            await query.edit_message_text("✅ ادمین با موفقیت حذف شد.")
        else:
            await query.edit_message_text("❌ ادمین یافت نشد!")
        await show_manage_admins(chat_id, context)

    # ---------------- اختصاص گروه به ادمین ----------------
    elif data.startswith("assign_group_menu:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
            return
        admin_id = data.split(":", 1)[1]
        await show_group_selection(chat_id, context, admin_id, message_id=message_id)

    # ---------------- toggle مجوز ----------------
    elif data.startswith("toggle_perm:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز تغییر مجوزها را ندارید!")
            return
        _, perm, target_type = data.split(":", 2)
        selected = context.user_data.get('selected_perms', set())
        if perm in selected:
            selected.remove(perm)
        else:
            selected.add(perm)
        context.user_data['selected_perms'] = selected
        target = (context.user_data.get('new_group_name') or 
                  context.user_data.get('editing_group') or 
                  context.user_data.get('new_admin_id') or 
                  context.user_data.get('editing_admin'))
        await show_permissions_selection(chat_id, context, target, is_group=(target_type == 'group'), message_id=message_id, show_desc=True)

    # ---------------- تأیید مجوزها ----------------
    elif data.startswith("confirm_perms:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز تأیید مجوزها را ندارید!")
            return
        target_type = data.split(":", 1)[1]
        selected = context.user_data.get('selected_perms', set())
        if target_type == 'admin':
            admin_id = context.user_data.get('new_admin_id') or context.user_data.get('editing_admin')
            if admin_id:
                admins[str(admin_id)] = selected
                save_data(data)
                await query.edit_message_text(
                    f"✅ {'ادمین با موفقیت اضافه شد' if context.user_data.get('new_admin_id') else 'مجوزهای ادمین با موفقیت ویرایش شد'}."
                )
        elif target_type == 'group':
            group_name = context.user_data.get('new_group_name') or context.user_data.get('editing_group')
            if group_name:
                groups[group_name] = selected
                save_data(data)
                await query.edit_message_text(
                    f"✅ {'گروه دسترسی با موفقیت ایجاد شد' if context.user_data.get('new_group_name') else 'مجوزهای گروه با موفقیت ویرایش شد'}."
                )
        context.user_data.clear()
        await show_main_menu(user_id, context)

    # ---------------- اختصاص گروه به ادمین ----------------
    elif data.startswith("assign_group:"):
        if not is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
            return
        _, group_name, admin_id = data.split(":")
        admin_id = int(admin_id)
        if group_name in groups:
            admins[str(admin_id)] = groups[group_name].copy()
            save_data(data)
            await query.edit_message_text(f"✅ گروه {group_name} با موفقیت به ادمین ID {admin_id} اختصاص یافت.")
        else:
            await query.edit_message_text(f"❌ گروه {group_name} یافت نشد!")
        context.user_data.clear()
        await show_main_menu(user_id, context)

    # ---------------- لغو ----------------
    elif data == "cancel_perms":
        context.user_data.clear()
        await query.edit_message_text("✅ عملیات با موفقیت لغو شد.")
        await show_main_menu(user_id, context)

# ======================== اجرای ربات ========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling()