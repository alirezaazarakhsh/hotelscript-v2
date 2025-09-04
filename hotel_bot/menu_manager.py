from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import MAX_BACKUPS, PERM_DISPLAY, SUPER_ADMINS
from access_manager import AccessManager

class MenuManager:
    @staticmethod
    async def show_main_menu(user_id, context, message_id=None, chat_id=None):
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
💰 **شارژ کیف پول** برای دسترسی به خدمات بیشتر
"""
        keyboard = []
        row = []
        if AccessManager.is_allowed(user_id, 'backup_db') or AccessManager.is_allowed(user_id, 'backup_media'):
            row.append(InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"))
        if AccessManager.is_allowed(user_id, 'list_backups'):
            row.append(InlineKeyboardButton("🗂 لیست بکاپ‌ها", callback_data="list_backups"))
        if row:
            keyboard.append(row)
        row = []
        if AccessManager.is_allowed(user_id, 'restore_db') or AccessManager.is_allowed(user_id, 'restore_media'):
            row.append(InlineKeyboardButton("🗃 ریستور بکاپ", callback_data="restore_backup"))
        if AccessManager.is_allowed(user_id, 'backup_info'):
            row.append(InlineKeyboardButton("📋 نحوه بکاپ‌گیری", callback_data="backup_info"))
        if row:
            keyboard.append(row)
        row = []
        if AccessManager.is_allowed(user_id, 'support'):
            row.append(InlineKeyboardButton("📮 پشتیبانی", callback_data="support"))
        if AccessManager.is_allowed(user_id, 'manage_admins'):
            row.append(InlineKeyboardButton("⚙️ کنترل پنل", callback_data="control_panel"))
        if row:
            keyboard.append(row)
        row = []
        row.append(InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge"))
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id and chat_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

    @staticmethod
    async def show_backup_menu(query, user_id, context):
        text = "📦 **انتخاب نوع بکاپ‌گیری**\n\nلازم به ذکر است که می‌توانید از دیتابیس یا فولدرهای مدیا بکاپ بگیرید.\n\n**توضیح**: بکاپ دیتابیس داده‌های سایت را حفظ می‌کند، بکاپ مدیا فایل‌های آپلود شده را."
        keyboard = [[
            InlineKeyboardButton("دیتابیس", callback_data="backup_db") if AccessManager.is_allowed(user_id, 'backup_db') else None,
            InlineKeyboardButton("فولدر مدیا", callback_data="backup_media") if AccessManager.is_allowed(user_id, 'backup_media') else None
        ]]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    @staticmethod
    async def show_backup_info(query, user_id, context):
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

    @staticmethod
    async def show_support_menu(query, user_id, context):
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

    @staticmethod
    async def show_restore_menu(query, user_id, context):
        text = (
            "📥 **منوی ریستور بکاپ**\n\n"
            "در این بخش می‌توانید فایل‌های بکاپ دیتابیس یا مدیا را به نسخه فعلی بازگردانید.\n"
            "**لطفاً دقت کنید:** ریستور بکاپ باعث جایگزینی فایل‌های موجود می‌شود!\n\n"
            "**توضیح**: قبل از ریستور، از وضعیت فعلی بکاپ بگیرید تا در صورت مشکل بتوانید بازگردانی کنید."
        )
        keyboard = [[
            InlineKeyboardButton("ریستور فولدر مدیا", callback_data="restore_media") if AccessManager.is_allowed(user_id, 'restore_media') else None,
            InlineKeyboardButton("ریستور دیتابیس", callback_data="restore_db") if AccessManager.is_allowed(user_id, 'restore_db') else None
        ]]
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        keyboard = [row for row in keyboard if any(row)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    @staticmethod
    async def show_control_panel(query, user_id, context):
        text = "⚙️ **کنترل پنل ربات**\n\n**توضیح**: در این بخش می‌توانید ادمین‌ها، گروه‌های دسترسی و رسیدهای پرداخت را مدیریت کنید."
        keyboard = [[
            InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin"),
            InlineKeyboardButton("👥 ایجاد گروه دسترسی", callback_data="create_group")
        ],[
            InlineKeyboardButton("🛠 مدیریت گروه‌های دسترسی", callback_data="manage_groups"),
            InlineKeyboardButton("👤 مدیریت ادمین‌ها", callback_data="manage_admins")
        ]]
        if user_id in SUPER_ADMINS:
            keyboard.append([InlineKeyboardButton("📜 لیست رسیدهای در حال انتظار", callback_data="pending_receipts")])
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")