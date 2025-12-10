import os
import logging
import re
import sys
import django
from jdatetime import datetime as jdatetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Setup Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safarname24.settings')
sys.path.insert(0, '/app')
django.setup()

from hotel_bot.config import BOT_TOKEN, SUPER_ADMINS, DB_BACKUP_DIR, MEDIA_BACKUP_DIR, MAX_BACKUPS
from hotel_bot.access_manager import AccessManager
from hotel_bot.backup_manager import BackupManager
from hotel_bot.file_manager import FileManager
from hotel_bot.menu_manager import MenuManager
from hotel_bot.admin_manager import AdminManager
from hotel_bot.group_manager import GroupManager
from hotel_bot.permission_manager import PermissionManager
from hotel_bot.wallet_manager import WalletManager
from hotel_bot.receipt_manager import ReceiptManager
from hotel_bot.reservation_manager import ReservationManager
from hotel_bot.points_manager import PointsManager

# Setup logging
logging.basicConfig(filename='/var/log/bot.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to send reservation notification
async def send_reservation_notification(tracking_code, buyer_name, hotel_name, capacity_status):
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    notification_text = f"🔔 **رزرو جدید ایجاد شد**\n\nکد پیگیری: {tracking_code}\nرزرو کننده: {buyer_name}\nهتل: {hotel_name}"
    
    keyboard = None
    if capacity_status == 'pending':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید رزرو", callback_data=f"approve_reservation::{tracking_code}")],
            [InlineKeyboardButton("❌ رد رزرو", callback_data=f"reject_reservation::{tracking_code}")]
        ])
    
    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=notification_text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to send notification to {admin_id}: {e}")

# Function to send payment receipt notification
async def send_payment_receipt_notification(tracking_code, buyer_phone, total_price, half_charge, wallet_withdrawal, discount, final_price, total_points, current_points, success=True):
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    
    if success:
        notification_text = f"""✅ پرداخت رزرو {tracking_code} موفق بود.
👤 کاربر: {buyer_phone}
💎 مجموع امتیاز باشگاه مشتریان: {current_points:,} امتیاز

📋 **صورتحساب:**
💰 مبلغ کل: {total_price:,} تومان
🏨 مبلغ نیم شارژ ورود و خروج: {half_charge:,} تومان
💳 مبلغ برداشت از کیف پول: {wallet_withdrawal:,} تومان
🎫 مبلغ استفاده شده در کد تخفیف: {discount:,} تومان
💵 مبلغ نهایی: {final_price:,} تومان
💎 امتیاز دریافتی برای اتاق: {total_points:,} امتیاز"""
    else:
        notification_text = f"❌ پرداخت رزرو {tracking_code} ناموفق بود.\n👤 کاربر: {buyer_phone}\n💰 مبلغ: {final_price:,} تومان"
    
    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=notification_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send payment notification to {admin_id}: {e}")

# Handler for /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['user_id'] = user_id
    if not AccessManager.is_allowed(user_id):
        await update.message.reply_text(
            "💢 دسترسی غیرفعال\n\nمتأسفانه شما مجاز به استفاده از خدمات این ربات نیستید، در صورتی که از فعال بودن اشتراک خود مطمئن هستید، لطفاً دوباره تلاش کنید."
        )
        return
    
    # بررسی و تمدید خودکار اشتراک‌ها
    AdminManager.check_and_auto_renew_subscriptions()
    
    await MenuManager.show_main_menu(user_id, context)

# Handler for button interactions
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    context.user_data['user_id'] = user_id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    await query.answer()
    logger.debug(f"Received callback data: {query.data}")

    if not AccessManager.is_allowed(user_id):
        # Check if subscription expired but allow wallet operations
        is_active, package, days_left = AdminManager.check_subscription_status(user_id)
        
        if not is_active:
            # Subscription expired, only allow wallet operations and subscription management
            allowed_callbacks = [
                "wallet_", "go_back", "payment:", "card_to_card", "send_receipt", 
                "cancel_", "renew_", "subscription_renewal", "my_subscription_status",
                "upgrade_my_package", "user_upgrade:", "execute_upgrade:"
            ]
            
            if not any(data.startswith(allowed) for allowed in allowed_callbacks):
                await query.edit_message_text(
                    "⏰ **اشتراک شما منقضی شده است**\n\nشما فقط می‌توانید کیف پول خود را شارژ کنید یا اشتراک را تمدید/ارتقا دهید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 تمدید اشتراک", callback_data="renew_subscription")],
                        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge")],
                        [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="support")]
                    ]),
                    parse_mode="Markdown"
                )
                return
        else:
            await query.edit_message_text(
                "💢 دسترسی غیرفعال\n\nمتأسفانه شما مجاز به استفاده از خدمات این ربات نیستید."
            )
            return

    data = query.data
    access_data = AccessManager.load_data()
    admins = access_data['admins']
    groups = access_data['groups']
    # Ensure groups is a dict with set values
    if not isinstance(groups, dict):
        groups = {}
    else:
        for gname in groups:
            if not isinstance(groups[gname], set):
                if isinstance(groups[gname], (list, set)):
                    groups[gname] = set(groups[gname])
                else:
                    groups[gname] = set()

    try:
        # Permission checks
        if data == "backup_menu" and not (AccessManager.is_allowed(user_id, 'backup_db') or AccessManager.is_allowed(user_id, 'backup_media')):
            await query.edit_message_text("❌ شما مجوز دسترسی به منوی بکاپ‌گیری را ندارید!")
            return
        if data == "backup_db" and not AccessManager.is_allowed(user_id, 'backup_db'):
            await query.edit_message_text("❌ شما مجوز بکاپ‌گیری از دیتابیس را ندارید!")
            return
        if data == "backup_media" and not AccessManager.is_allowed(user_id, 'backup_media'):
            await query.edit_message_text("❌ شما مجوز بکاپ‌گیری از مدیا را ندارید!")
            return
        if data == "backup_info" and not AccessManager.is_allowed(user_id, 'backup_info'):
            await query.edit_message_text("❌ شما مجوز مشاهده اطلاعات بکاپ را ندارید!")
            return
        if data == "support" and not AccessManager.is_allowed(user_id, 'support'):
            await query.edit_message_text("❌ شما مجوز دسترسی به پشتیبانی را ندارید!")
            return
        if data == "view_reservations" and not AccessManager.is_allowed(user_id, 'view_reservations'):
            await query.edit_message_text("❌ شما مجوز مشاهده رزروها را ندارید!")
            return
        if data.startswith("approve_reservation::") and not AccessManager.is_allowed(user_id, 'approve_reservations'):
            await query.edit_message_text("❌ شما مجوز تایید رزروها را ندارید!")
            return
        if data.startswith("reject_reservation::") and not AccessManager.is_allowed(user_id, 'approve_reservations'):
            await query.edit_message_text("❌ شما مجوز رد رزروها را ندارید!")
            return
        if data.startswith("pending_reservation::") and not AccessManager.is_allowed(user_id, 'approve_reservations'):
            await query.edit_message_text("❌ شما مجوز تغییر وضعیت رزروها را ندارید!")
            return
        if data == "view_balance" and not AccessManager.is_allowed(user_id, 'view_balance'):
            await query.edit_message_text("❌ شما مجوز مشاهده موجودی کیف پول را ندارید!")
            return
        if data.startswith("charge_admin_wallet:") and not AccessManager.is_allowed(user_id, 'manage_wallet'):
            await query.edit_message_text("❌ شما مجوز شارژ کیف پول دیگران را ندارید!")
            return
        if data == "manage_wallet" and not AccessManager.is_allowed(user_id, 'manage_wallet'):
            await query.edit_message_text("❌ شما مجوز مدیریت کیف پول کاربران را ندارید!")
            return
        if data == "manage_points" and not AccessManager.is_allowed(user_id, 'manage_points'):
            await query.edit_message_text("❌ شما مجوز مدیریت امتیازات باشگاه مشتریان را ندارید!")
            return
        if data.startswith("edit_admin_profile_field:") and not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش پروفایل ادمین را ندارید!")
            return
        if data.startswith("set_expiry:") and not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز تنظیم مدت زمان را ندارید!")
            return
        if data.startswith("edit_profile_field:") and not AccessManager.is_allowed(user_id, 'edit_profile'):
            await query.edit_message_text("❌ شما مجوز ویرایش این بخش از پروفایل را ندارید!")
            return
        if data.startswith("edit_admin_profile_field:") and not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش این بخش از پروفایل ادمین را ندارید!")
            return

        # Handlers
        if data == "backup_menu":
            await MenuManager.show_backup_menu(query, user_id, context)
        elif data == "backup_db":
            await BackupManager.backup_database(user_id, context)
        elif data == "backup_media":
            await BackupManager.backup_media(user_id, context)
        elif data == "backup_info":
            await MenuManager.show_backup_info(query, user_id, context)
        elif data == "view_reservations":
            await ReservationManager.list_all_reservations(user_id, context, query=query)
        elif data == "view_reservations_return":
            # Return to saved page and search
            saved_page = context.user_data.get('reservation_page', 1)
            saved_search = context.user_data.get('reservation_search')
            await ReservationManager.list_all_reservations(user_id, context, page=saved_page, search_query=saved_search, query=query)
        elif data.startswith("list_reservations_page::"):
            parts = data.split("::")
            page = int(parts[1])
            search_query = parts[2] if len(parts) > 2 and parts[2] else None
            await ReservationManager.list_all_reservations(user_id, context, page=page, search_query=search_query, query=query)
        elif data == "search_reservations":
            await ReservationManager.search_reservations(user_id, context)
        elif data.startswith("view_reservation_details::"):
            tracking_code = data.split("::", 1)[1]
            await ReservationManager.view_reservation_details(user_id, context, tracking_code)
        elif data.startswith("approve_reservation::"):
            tracking_code = data.split("::", 1)[1]
            await ReservationManager.approve_reservation(user_id, context, tracking_code)
        elif data.startswith("reject_reservation::"):
            tracking_code = data.split("::", 1)[1]
            await ReservationManager.reject_reservation(user_id, context, tracking_code)
        elif data.startswith("pending_reservation::"):
            tracking_code = data.split("::", 1)[1]
            await ReservationManager.pending_reservation(user_id, context, tracking_code)
        elif data == "upgrade_requests":
            await query.edit_message_text(
                "ویژگی ارتقای تعداد درخواست‌ها به‌زودی در دسترس خواهد بود، برای جزئیات بیشتر می‌توانید با پشتیبانی در ارتباط باشید.\n\n**توضیح**: این ارتقا اجازه بکاپ‌های بیشتر یا ویژگی‌های پیشرفته را فراهم می‌کند.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="backup_info")]]),
                parse_mode="Markdown"
            )
        elif data == "go_back":
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "support":
            await MenuManager.show_support_menu(query, user_id, context)
        elif data == "control_panel":
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز دسترسی به کنترل پنل را ندارید!")
                return
            await MenuManager.show_control_panel(query, user_id, context)
        elif data == "add_admin":
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز افزودن ادمین را ندارید!")
                return
            context.user_data['state'] = 'waiting_for_admin_id'
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً ID عددی کاربر را ارسال کنید.\n\n**توضیح**: ID کاربر را از تنظیمات تلگرام یا بات‌های دیگر می‌توانید پیدا کنید.",
                parse_mode="Markdown"
            )
        elif data == "create_group":
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز ایجاد گروه دسترسی را ندارید!")
                return
            context.user_data['state'] = 'waiting_for_group_name'
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً نام گروه دسترسی را ارسال کنید.\n\n**توضیح**: نام گروه باید منحصر به فرد باشد و برای شناسایی نقش استفاده می‌شود.",
                parse_mode="Markdown"
            )
        elif data == "manage_groups":
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مدیریت گروه‌های دسترسی را ندارید!")
                return
            await GroupManager.show_manage_groups(chat_id, context, groups, message_id=message_id)
        elif data == "manage_admins":
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
                return
            await AdminManager.show_manage_admins(chat_id, context, admins, message_id=message_id)
        elif data.startswith("view_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مشاهده گروه را ندارید!")
                return
            try:
                group_name = data.split(":", 1)[1]
                await GroupManager.show_group_details(chat_id, context, group_name, groups, message_id=message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("view_admin:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مشاهده ادمین را ندارید!")
                return
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.show_admin_details(chat_id, context, admin_id, admins, groups, message_id=message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("edit_group_perms:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز ویرایش گروه را ندارید!")
                return
            try:
                group_name = data.split(":", 1)[1]
                context.user_data['editing_group'] = group_name
                context.user_data['selected_perms'] = groups.get(group_name, set())
                context.user_data['state'] = 'select_group_permissions'
                await PermissionManager.show_permissions_selection(chat_id, context, group_name, is_group=True, message_id=message_id, show_desc=True)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("rename_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز تغییر نام گروه را ندارید!")
                return
            try:
                group_name = data.split(":", 1)[1]
                context.user_data['editing_group'] = group_name
                context.user_data['state'] = 'waiting_for_new_group_name'
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="لطفاً نام جدید گروه را ارسال کنید.\n\n**توضیح**: نام جدید باید منحصر به فرد باشد.",
                    parse_mode="Markdown"
                )
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("delete_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز حذف گروه را ندارید!")
                return
            try:
                group_name = data.split(":", 1)[1]
                if group_name in groups:
                    del groups[group_name]
                    AccessManager.save_data(access_data)
                    await query.edit_message_text("✅ گروه با موفقیت حذف شد.")
                else:
                    await query.edit_message_text("❌ گروه یافت نشد!")
                await GroupManager.show_manage_groups(chat_id, context, groups)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("delete_admin:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز حذف ادمین را ندارید!")
                return
            try:
                admin_id = data.split(":", 1)[1]
                if admin_id in admins:
                    del admins[admin_id]
                    AccessManager.save_data(access_data)
                    await query.edit_message_text("✅ ادمین با موفقیت حذف شد.")
                else:
                    await query.edit_message_text("❌ ادمین یافت نشد!")
                await AdminManager.show_manage_admins(chat_id, context, admins)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("assign_group_menu:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
                return
            try:
                admin_id = data.split(":", 1)[1]
                await PermissionManager.show_group_selection(chat_id, context, admin_id, groups, message_id=message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("toggle_perm:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز تغییر مجوزها را ندارید!")
                return
            try:
                _, perm, target_type = data.split(":", 2)
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
                return
            if target_type != 'group':
                return
            selected = context.user_data.get('selected_perms', set())
            if perm in selected:
                selected.remove(perm)
            else:
                selected.add(perm)
            context.user_data['selected_perms'] = selected
            target = context.user_data.get('new_group_name') or context.user_data.get('editing_group')
            await PermissionManager.show_permissions_selection(chat_id, context, target, is_group=True, message_id=message_id, show_desc=True)
        elif data.startswith("confirm_perms:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز تأیید مجوزها را ندارید!")
                return
            try:
                target_type = data.split(":", 1)[1]
                if target_type != 'group':
                    return
                selected = context.user_data.get('selected_perms', set())
                group_name = context.user_data.get('new_group_name') or context.user_data.get('editing_group')
                if group_name:
                    groups[group_name] = selected
                    AccessManager.save_data(access_data)
                    await query.edit_message_text(
                        f"✅ {'گروه دسترسی با موفقیت ایجاد شد' if context.user_data.get('new_group_name') else 'مجوزهای گروه با موفقیت ویرایش شد'}."
                    )
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("assign_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
                return
            try:
                _, group_name, admin_id = data.split(":")
                if group_name in groups:
                    admins[str(admin_id)] = group_name
                    AccessManager.save_data(access_data)
                    await query.edit_message_text(f"✅ گروه {group_name} با موفقیت به ادمین ID {admin_id} اختصاص یافت.")
                else:
                    await query.edit_message_text(f"❌ گروه {group_name} یافت نشد!")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "cancel_perms":
            context.user_data.clear()
            await query.edit_message_text("✅ عملیات با موفقیت لغو شد.")
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "wallet_charge":
            await WalletManager.show_wallet_menu(chat_id, context, message_id)
        elif data == "card_to_card":
            await WalletManager.prompt_for_amount(chat_id, context)
        elif data == "send_receipt":
            await WalletManager.prompt_for_receipt(chat_id, context, message_id)
        elif data == "cancel_card_to_card":
            context.user_data.clear()
            await WalletManager.show_wallet_menu(chat_id, context, message_id)
        elif data == "wallet_menu":
            await WalletManager.show_wallet_menu(chat_id, context, message_id)
        elif data == "view_balance":
            await WalletManager.show_balance(chat_id, context, user_id, message_id)
        elif data == "pending_receipts":
            if user_id in SUPER_ADMINS:
                await ReceiptManager.show_pending_receipts(chat_id, context, message_id)
            else:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
        elif data.startswith("confirm_receipt:"):
            if user_id not in SUPER_ADMINS:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
                return
            match = re.match(r'^confirm_receipt:(\d+):(\d+):(\d+)$', data)
            if not match:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ داده‌های نامعتبر!", parse_mode="Markdown")
                return
            u_id, amount, idx = match.groups()
            receipts = ReceiptManager.load_receipts()
            if u_id in receipts and int(idx) < len(receipts[u_id]):
                msg = await ReceiptManager.confirm_receipt(context, u_id, int(amount), int(idx))
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, parse_mode="Markdown")
                await ReceiptManager.show_pending_receipts(chat_id, context, message_id)
            else:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ رسید یافت نشد!", parse_mode="Markdown")
        elif data.startswith("reject_receipt:"):
            if user_id not in SUPER_ADMINS:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
                return
            match = re.match(r'^reject_receipt:(\d+):(\d+)$', data)
            if not match:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ داده‌های نامعتبر!", parse_mode="Markdown")
                return
            u_id, idx = match.groups()
            msg = await ReceiptManager.reject_receipt(context, u_id, int(idx))
            await query.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, parse_mode="Markdown")
            await ReceiptManager.show_pending_receipts(chat_id, context, message_id)
        elif data.startswith("view_receipt:"):
            if user_id not in SUPER_ADMINS:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
                return
            match = re.match(r'^view_receipt:(\d+):(\d+)$', data)
            if not match:
                await query.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ داده‌های نامعتبر!", parse_mode="Markdown")
                return
            u_id, idx = match.groups()
            msg = await ReceiptManager.view_receipt(context, u_id, int(idx), chat_id=chat_id)
            await query.message.reply_text(text=msg, parse_mode="Markdown")
            await ReceiptManager.show_pending_receipts(chat_id, context, message_id)
        elif data.startswith("charge_admin_wallet:"):
            try:
                admin_id = data.split(":", 1)[1]
                await UserWalletManager.prompt_for_admin_wallet_charge(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("view_wallet:"):
            if user_id in SUPER_ADMINS:
                try:
                    admin_id = data.split(":", 1)[1]
                    wallets = ReceiptManager.load_wallets()
                    balance = wallets.get(str(admin_id), 0)
                    await query.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"💰 **موجودی کیف پول ادمین {admin_id}**\n\nموجودی فعلی: {balance:,} تومان",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=f"view_admin:{admin_id}")]]),
                        parse_mode="Markdown"
                    )
                except IndexError:
                    await query.edit_message_text("❌ داده نامعتبر!")
                except Exception as e:
                    logger.error(f"Error viewing wallet for admin_id {admin_id}: {str(e)}")
                    await query.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"❌ خطا در نمایش موجودی کیف پول: {str(e)}",
                        parse_mode="Markdown"
                    )
            else:
                await query.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ شما مجوز دسترسی ندارید!",
                    parse_mode="Markdown"
                )
        elif data.startswith("modify_wallet:"):
            if user_id in SUPER_ADMINS:
                try:
                    admin_id = data.split(":", 1)[1]
                    context.user_data['state'] = 'waiting_for_wallet_modification'
                    context.user_data['target_admin_id'] = admin_id
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="لطفاً مقدار تغییر موجودی (مثبت برای افزایش، منفی برای کاهش) را به تومان وارد کنید.\n\n**مثال**: 500000 برای افزایش 500,000 تومان یا -500000 برای کاهش 500,000 تومان.",
                        parse_mode="Markdown"
                    )
                except IndexError:
                    await query.edit_message_text("❌ داده نامعتبر!")
            else:
                await query.edit_message_text("❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
        elif data.startswith("wallet_page:"):
            try:
                parts = data.split(":", 2)
                page = int(parts[1])
                search_query = parts[2] if len(parts) > 2 and parts[2] else None
                await MenuManager.show_manage_wallet_menu(query, user_id, context, page, search_query)
            except (ValueError, IndexError):
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "manage_wallet":
            await MenuManager.show_manage_wallet_menu(query, user_id, context)
        elif data == "search_wallet_users":
            await MenuManager.search_wallet_users(user_id, context)
        elif data.startswith("points_page:"):
            try:
                page = int(data.split(":", 1)[1])
                await MenuManager.show_manage_points_menu(query, user_id, context, page)
            except (ValueError, IndexError):
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "manage_points":
            await MenuManager.show_points_main_menu(query, user_id, context)
        elif data == "view_points_users":
            await MenuManager.show_manage_points_menu(query, user_id, context)
        elif data.startswith("manage_user_wallet:"):
            try:
                user_target_id = data.split(":", 1)[1]
                await WalletManager.show_user_wallet_management(query, user_id, context, user_target_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("manage_user_points:"):
            try:
                user_target_id = data.split(":", 1)[1]
                await PointsManager.show_user_points_management(query, user_id, context, user_target_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("charge_wallet:"):
            try:
                phone = data.split(":", 1)[1]
                context.user_data['wallet_phone'] = phone
                context.user_data['state'] = 'waiting_for_wallet_amount'
                await query.edit_message_text(
                    "💰 مبلغ افزایش موجودی را به تومان وارد کنید (حداقل 1,000 تومان):",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data="go_back")]]),
                    parse_mode="Markdown"
                )
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "edit_profile":
            await MenuManager.show_profile_edit_menu(query, user_id, context)
        elif data.startswith("edit_profile_field:"):
            try:
                _, field, target_id = data.split(":")
                context.user_data['state'] = f'waiting_for_{field}'
                context.user_data['target_id'] = target_id
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
            await query.edit_message_text(
                f"لطفاً {field.replace('_', ' ')} خود را وارد کنید (اختیاری).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data="go_back")]]),
                parse_mode="Markdown"
            )
        elif data.startswith("edit_admin_profile:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.show_edit_admin_profile(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("edit_admin_profile_field:"):
            try:
                _, field, admin_id = data.split(":")
                context.user_data['state'] = f'waiting_for_{field}'
                context.user_data['target_id'] = admin_id
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
            await query.edit_message_text(
                f"لطفاً {field.replace('_', ' ')} ادمین {admin_id} را وارد کنید (اختیاری).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f"view_admin:{admin_id}")]]),
                parse_mode="Markdown"
            )
        elif data.startswith("subscription_renewal:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.show_subscription_renewal(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("manage_subscription:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مدیریت اشتراک را ندارید!")
                return
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.manage_subscription_profile(chat_id, context, admin_id, message_id=message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "cancel_subscription_setup":
            context.user_data.pop('setting_subscription_for', None)
            context.user_data.pop('subscription_step', None)
            await query.edit_message_text("❌ تنظیم اشتراک لغو شد.")
        elif data.startswith("renew_monthly:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.process_subscription_renewal(chat_id, context, admin_id, "monthly")
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("renew_yearly:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.process_subscription_renewal(chat_id, context, admin_id, "yearly")
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("change_package:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.show_package_selection(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("set_expiry_date:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.prompt_expiry_date(chat_id, context, admin_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("toggle_auto_renewal:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.toggle_auto_renewal(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("cancel_subscription:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.cancel_subscription(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("set_subscription_status:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.show_status_options(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("set_status:"):
            try:
                parts = data.split(":")
                status = parts[1]
                admin_id = parts[2]
                await AdminManager.set_subscription_status(chat_id, context, status, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("select_package:"):
            try:
                parts = data.split(":")
                admin_id = parts[1]
                package_id = parts[2]
                await AdminManager.change_package(chat_id, context, admin_id, package_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "insufficient_balance":
            await query.edit_message_text(
                "❌ **موجودی کافی نیست**\n\nبرای تمدید اشتراک، ابتدا کیف پول خود را شارژ کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge")],
                    [InlineKeyboardButton("بازگشت", callback_data="go_back")]
                ]),
                parse_mode="Markdown"
            )
        # Subscription management callbacks
        elif data == "manage_subscriptions":
            await AdminManager.show_subscription_management(chat_id, context, message_id)
        elif data.startswith("package_details:"):
            try:
                package_id = data.split(":", 1)[1]
                await AdminManager.show_package_details(chat_id, context, package_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "create_new_package":
            await AdminManager.create_new_package(chat_id, context, message_id)
        elif data.startswith("select_package_group:"):
            try:
                group_name = data.split(":", 1)[1]
                await AdminManager.select_package_group(chat_id, context, group_name, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "finish_package_creation":
            await AdminManager.finish_package_creation(chat_id, context)
        elif data == "cancel_create_package":
            context.user_data.pop('creating_package', None)
            await query.edit_message_text("❌ ایجاد پکیج لغو شد.")
            await AdminManager.show_subscription_management(chat_id, context)
        elif data.startswith("assign_package:"):
            try:
                package_id = data.split(":", 1)[1]
                await AdminManager.assign_package_to_admin(chat_id, context, package_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("confirm_assign:"):
            try:
                _, package_id, admin_id = data.split(":")
                await AdminManager.confirm_package_assignment(chat_id, context, package_id, admin_id, message_id)
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "view_subscription_status":
            await AdminManager.view_subscription_status(chat_id, context, message_id)
        elif data.startswith("upgrade_package:"):
            try:
                admin_id = data.split(":", 1)[1]
                await AdminManager.upgrade_admin_package(chat_id, context, admin_id, message_id)
            except IndexError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data.startswith("confirm_upgrade:"):
            try:
                _, admin_id, new_package_id = data.split(":")
                await AdminManager.confirm_package_upgrade(chat_id, context, admin_id, new_package_id, message_id)
            except ValueError:
                await query.edit_message_text("❌ داده نامعتبر!")
        elif data == "my_subscription_status":
            await AdminManager.show_user_subscription_status(chat_id, context, message_id)
        elif data == "renew_subscription":
            await AdminManager.renew_subscription(chat_id, context, message_id)
        elif data == "confirm_renewal":
            await AdminManager.confirm_subscription_renewal(chat_id, context, message_id)
        elif data == "cancel_renewal":
            await query.edit_message_text("❌ تمدید اشتراک لغو شد.")
            await AdminManager.show_user_subscription_status(chat_id, context)
        elif data == "upgrade_my_package":
            await AdminManager.upgrade_user_package(chat_id, context, message_id)
        elif data.startswith("user_upgrade:"):
            package_id = data.split(":", 1)[1]
            await AdminManager.confirm_user_package_upgrade(chat_id, context, package_id, message_id)
        elif data.startswith("execute_upgrade:"):
            package_id = data.split(":", 1)[1]
            await AdminManager.execute_user_package_upgrade(chat_id, context, package_id, message_id)
        elif data == "assign_package_menu":
            # Show menu for assigning packages to admins
            await AdminManager.show_subscription_management(chat_id, context, message_id)

    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        try:
            await query.edit_message_text(f"❌ خطایی رخ داد: {str(e)}")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطایی رخ داد: {str(e)}")
        context.user_data.clear()
        await MenuManager.show_main_menu(user_id, context)

# Handler for text and file messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['user_id'] = user_id
    state = context.user_data.get('state')
    logger.debug(f"Handling message for user {user_id}, state: {state}, message type: {type(update.message).__name__}, content: {update.message.text if update.message.text else 'No text'}")
    text = update.message.text if update.message.text else "No text"
    data = AccessManager.load_data()
    admins = data['admins']
    groups = data['groups']
    profiles = data.get('profiles', {})

    try:
        if state == 'waiting_for_admin_id':
            try:
                new_id = int(text)
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک ID عددی معتبر وارد کنید (فقط اعداد).")
                return
            if str(new_id) in admins or new_id in SUPER_ADMINS:
                await update.message.reply_text("❌ این کاربر قبلاً ادمین یا سوپرادمین است!")
                return
            context.user_data['new_admin_id'] = new_id
            if not groups:
                await update.message.reply_text(
                    "❌ هیچ گروه دسترسی‌ای وجود ندارد. ابتدا یک گروه دسترسی ایجاد کنید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]
                    ])
                )
                context.user_data.clear()
                return
            await PermissionManager.show_group_selection(update.message.chat_id, context, new_id, groups)
        elif state == 'waiting_for_group_name':
            group_name = text.strip()
            if not group_name:
                await update.message.reply_text("❌ نام گروه نمی‌تواند خالی باشد!")
                return
            if group_name in groups:
                await update.message.reply_text("❌ این گروه قبلاً وجود دارد!")
                return
            context.user_data['new_group_name'] = group_name
            context.user_data['selected_perms'] = set()
            context.user_data['state'] = 'select_group_permissions'
            await PermissionManager.show_permissions_selection(
                update.message.chat_id, context, group_name, is_group=True, show_desc=True
            )
        elif state == 'waiting_for_new_group_name':
            new_name = text.strip()
            if not new_name:
                await update.message.reply_text("❌ نام جدید گروه نمی‌تواند خالی باشد!")
                return
            old_name = context.user_data.get('editing_group')
            if not old_name:
                await update.message.reply_text("❌ گروه در حال ویرایش یافت نشد!")
                context.user_data.clear()
                return
            if new_name != old_name and new_name in groups:
                await update.message.reply_text("❌ این نام گروه قبلاً وجود دارد!")
                return
            groups[new_name] = groups.pop(old_name)
            AccessManager.save_data(data)
            await update.message.reply_text(f"✅ نام گروه به {new_name} تغییر یافت.")
            context.user_data.clear()
            await GroupManager.show_manage_groups(update.message.chat_id, context, groups)
        elif state == 'waiting_for_amount':
            try:
                amount = int(text)
                if amount < 1000000:
                    raise ValueError("مبلغ کمتر از حداقل مجاز است")
                context.user_data['amount'] = amount
                await WalletManager.show_card_details(update.message.chat_id, context, amount)
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. حداقل 1,000,000 تومان و فقط اعداد.")
                context.user_data.clear()
                await WalletManager.show_wallet_menu(update.message.chat_id, context)
        elif state == 'waiting_for_receipt':
            try:
                logger.debug(f"User {user_id} sent message: photo={bool(update.message.photo)}, document={bool(update.message.document)}, user_data={context.user_data}")
                if not update.message:
                    logger.error(f"No message received for user {user_id} in waiting_for_receipt state")
                    await update.message.reply_text("❌ خطا: هیچ پیامی دریافت نشد!")
                    return
                if 'receipt_processed' in context.user_data and context.user_data['receipt_processed']:
                    logger.warning(f"Receipt already processed for user {user_id}, skipping.")
                    return
                receipt_file_id = None
                is_photo = False
                if update.message.photo:
                    receipt_file_id = update.message.photo[-1].file_id
                    is_photo = True
                    logger.debug(f"Photo receipt received: {receipt_file_id}")
                elif update.message.document and update.message.document.mime_type in ['application/pdf', 'image/jpeg', 'image/png']:
                    receipt_file_id = update.message.document.file_id
                    logger.debug(f"Document receipt received: {receipt_file_id}")
                else:
                    logger.warning(f"Invalid file type: {update.message.document.mime_type if update.message.document else 'No document'}")
                    await update.message.reply_text(
                        "❌ لطفاً رسید را به صورت عکس (JPEG/PNG) یا فایل PDF ارسال کنید."
                    )
                    return
                amount = context.user_data.get('amount')
                if not amount:
                    logger.error(f"No amount found in user_data: {context.user_data}")
                    await update.message.reply_text(
                        "❌ خطا: مبلغ پرداخت مشخص نشده است. لطفاً دوباره شروع کنید."
                    )
                    context.user_data.clear()
                    await WalletManager.show_wallet_menu(update.message.chat_id, context)
                    return
                logger.debug(f"Calling add_receipt with user_id={user_id}, amount={amount}, receipt_file_id={receipt_file_id}, is_photo={is_photo}")
                await ReceiptManager.add_receipt(context, user_id, amount, receipt_file_id, is_photo)
                await update.message.reply_text(
                    "✅ رسید ارسال شد و در حال بررسی توسط ادمین است."
                )
                context.user_data['receipt_processed'] = True
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Error processing receipt for user {user_id}: {str(e)}")
                await update.message.reply_text(
                    f"❌ خطا در ثبت رسید: {str(e)}. لطفاً دوباره تلاش کنید."
                )
                context.user_data.clear()
                await WalletManager.show_wallet_menu(update.message.chat_id, context)
        elif state == 'waiting_for_admin_wallet_amount':
            try:
                amount = int(text)
                if amount < 1000000:
                    raise ValueError("مبلغ کمتر از حداقل مجاز است")
                target_admin_id = context.user_data['target_admin_id']
                wallets = ReceiptManager.load_wallets()
                wallets[str(target_admin_id)] = wallets.get(str(target_admin_id), 0) + amount
                ReceiptManager.save_wallets(wallets)
                await update.message.reply_text(f"✅ کیف پول ادمین {target_admin_id} به مبلغ {amount:,} تومان شارژ شد.")
                await context.bot.send_message(
                    chat_id=target_admin_id,
                    text=f"✅ کیف پول شما به مبلغ {amount:,} تومان توسط سوپرادمین شارژ شد."
                )
                context.user_data.clear()
                await AdminManager.show_manage_admins(update.message.chat_id, context, admins)
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. حداقل 1,000,000 تومان و فقط اعداد.")
        elif state == 'waiting_for_wallet_modification':
            try:
                amount = int(text)
                target_admin_id = context.user_data['target_admin_id']
                wallets = ReceiptManager.load_wallets()
                current_balance = wallets.get(str(target_admin_id), 0)
                new_balance = current_balance + amount
                if new_balance < 0:
                    raise ValueError("موجودی نمی‌تواند منفی شود!")
                wallets[str(target_admin_id)] = new_balance
                ReceiptManager.save_wallets(wallets)
                await update.message.reply_text(
                    f"✅ موجودی کیف پول ادمین {target_admin_id} به مبلغ {new_balance:,} تومان تغییر یافت (تغییر: {amount:+,} تومان)."
                )
                await context.bot.send_message(
                    chat_id=target_admin_id,
                    text=f"✅ موجودی کیف پول شما به مبلغ {new_balance:,} تومان توسط سوپرادمین تغییر یافت (تغییر: {amount:+,} تومان)."
                )
                context.user_data.clear()
                await AdminManager.show_admin_details(update.message.chat_id, context, target_admin_id, admins, groups)
            except ValueError as e:
                await update.message.reply_text(f"❌ خطا: {str(e)}")
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Error modifying wallet for user {target_admin_id}: {str(e)}")
                await update.message.reply_text(f"❌ خطا در تغییر موجودی: {str(e)}")
                context.user_data.clear()
        elif state in ['waiting_for_name', 'waiting_for_lastname', 'waiting_for_national_id', 'waiting_for_phone', 'waiting_for_landline', 'waiting_for_company_name', 'waiting_for_company_reg']:
            target_id = context.user_data.get('target_id')
            access_data = AccessManager.load_data()
            profiles = access_data.get('profiles', {})
            if target_id not in profiles:
                profiles[target_id] = {}
            if state == 'waiting_for_name':
                profiles[target_id]['name'] = text if text else profiles[target_id].get('name', '')
            elif state == 'waiting_for_lastname':
                profiles[target_id]['lastname'] = text if text else profiles[target_id].get('lastname', '')
            elif state == 'waiting_for_national_id':
                profiles[target_id]['national_id'] = text if text else profiles[target_id].get('national_id', '')
            elif state == 'waiting_for_phone':
                profiles[target_id]['phone'] = text if text else profiles[target_id].get('phone', '')
            elif state == 'waiting_for_landline':
                profiles[target_id]['landline'] = text if text else profiles[target_id].get('landline', '')
            elif state == 'waiting_for_company_name':
                profiles[target_id]['company_name'] = text if text else profiles[target_id].get('company_name', '')
            elif state == 'waiting_for_company_reg':
                profiles[target_id]['company_reg'] = text if text else profiles[target_id].get('company_reg', '')
            access_data['profiles'] = profiles
            AccessManager.save_data(access_data)
            await update.message.reply_text(
                f"✅ {state.replace('waiting_for_', '').replace('_', ' ')} با موفقیت ثبت شد."
            )
            context.user_data.clear()
            if str(user_id) == target_id:
                await MenuManager.show_profile_edit_menu(update.message, user_id, context)
            else:
                await AdminManager.show_edit_admin_profile(update.message.chat_id, context, target_id)
        elif state == 'waiting_for_expiry_date':
            target_admin_id = context.user_data.get('target_admin_id')
            if not target_admin_id:
                await update.message.reply_text("❌ ادمین یافت نشد. دوباره شروع کنید.")
                context.user_data.clear()
                return
            expiry_date = text.strip()
            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            if str(target_admin_id) not in admins:
                await update.message.reply_text("❌ ادمین یافت نشد.")
                context.user_data.clear()
                return
            admin_data = admins.get(str(target_admin_id), {})
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}
            if expiry_date == '0':
                admin_data.pop('license_expiry', None)
                message = f"✅ دسترسی ادمین {target_admin_id} دائمی تنظیم شد."
            else:
                from datetime import datetime
                try:
                    datetime.fromisoformat(expiry_date)
                    admin_data['license_expiry'] = expiry_date
                    message = f"✅ تاریخ انقضای دسترسی ادمین {target_admin_id} به {expiry_date} تنظیم شد."
                except ValueError:
                    await update.message.reply_text("❌ فرمت تاریخ نامعتبر. از فرمت YYYY-MM-DD استفاده کنید.")
                    return
            admins[str(target_admin_id)] = admin_data
            access_data['admins'] = admins
            AccessManager.save_data(access_data)
            await update.message.reply_text(message)
            context.user_data.clear()
            await AdminManager.show_manage_admins(update.message.chat_id, context, admins)
        elif state == 'waiting_for_wallet_phone':
            phone = text.strip()
            if not phone.isdigit() or len(phone) != 11 or not phone.startswith('09'):
                await update.message.reply_text("❌ شماره موبایل نامعتبر. باید 11 رقم و با 09 شروع شود.")
                return
            # Show wallet balance
            from finance.models import Wallet
            from authentication.models import BaseUser
            from asgiref.sync import sync_to_async
            try:
                user = await sync_to_async(BaseUser.objects.get)(phone_number=phone)
                wallet, created = await sync_to_async(Wallet.objects.get_or_create)(user=user, defaults={'balance': 0})
                text = f"💰 **موجودی کیف پول کاربر {phone}**\n\nموجودی فعلی: {wallet.balance:,} تومان\n\nآیا می‌خواهید موجودی را افزایش دهید؟"
                keyboard = [
                    [InlineKeyboardButton("✅ بله، افزایش موجودی", callback_data=f"charge_wallet:{phone}")],
                    [InlineKeyboardButton("❌ خیر، بازگشت", callback_data="go_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            except BaseUser.DoesNotExist:
                await update.message.reply_text("❌ کاربری با این شماره موبایل یافت نشد.")
            except Exception as e:
                logger.error(f"Error getting wallet balance: {e}")
                await update.message.reply_text(f"❌ خطا در دریافت موجودی: {str(e)}")
            context.user_data.clear()
        elif state == 'waiting_for_wallet_amount':
            try:
                amount = int(text.replace(',', ''))
                if amount < 1000:
                    raise ValueError("مبلغ کمتر از حداقل مجاز است")
                phone = context.user_data.get('wallet_phone')
                if not phone:
                    await update.message.reply_text("❌ شماره موبایل یافت نشد. دوباره شروع کنید.")
                    context.user_data.clear()
                    return
                # Charge wallet
                from finance.models import Wallet
                from authentication.models import BaseUser
                from asgiref.sync import sync_to_async
                try:
                    user = await sync_to_async(BaseUser.objects.get)(phone_number=phone)
                    wallet, created = await sync_to_async(Wallet.objects.get_or_create)(user=user, defaults={'balance': 0})
                    await sync_to_async(wallet.__class__.objects.filter(pk=wallet.pk).update)(balance=wallet.balance + amount)
                    await update.message.reply_text(f"✅ کیف پول کاربر {phone} به مبلغ {amount:,} تومان شارژ شد.\nموجودی جدید: {(wallet.balance + amount):,} تومان")
                except BaseUser.DoesNotExist:
                    await update.message.reply_text("❌ کاربری با این شماره موبایل یافت نشد.")
                except Exception as e:
                    logger.error(f"Error charging wallet: {e}")
                    await update.message.reply_text(f"❌ خطا در شارژ کیف پول: {str(e)}")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. حداقل 1,000 تومان و فقط اعداد.")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
        elif state == 'waiting_for_wallet_adjustment':
            try:
                amount = int(text.replace(',', ''))
                target_user_id = context.user_data.get('managing_wallet_user_id')
                if not target_user_id:
                    await update.message.reply_text("❌ کاربر یافت نشد. دوباره شروع کنید.")
                    context.user_data.clear()
                    return
                # Adjust wallet
                from finance.models import Wallet
                from authentication.models import BaseUser
                from asgiref.sync import sync_to_async
                try:
                    user = await sync_to_async(BaseUser.objects.get)(id=target_user_id)
                    wallet, created = await sync_to_async(Wallet.objects.get_or_create)(user=user, defaults={'balance': 0})
                    old_balance = wallet.balance
                    wallet.balance += amount
                    await sync_to_async(wallet.save)()
                    new_balance = wallet.balance
                    await update.message.reply_text(f"✅ کیف پول کاربر {user.phone_number} به مبلغ {amount:,} تومان {'افزایش' if amount > 0 else 'کاهش'} یافت.\nموجودی قبلی: {old_balance:,} تومان\nموجودی جدید: {new_balance:,} تومان")
                except BaseUser.DoesNotExist:
                    await update.message.reply_text("❌ کاربر یافت نشد.")
                except Exception as e:
                    logger.error(f"Error adjusting wallet: {e}")
                    await update.message.reply_text(f"❌ خطا در تنظیم کیف پول: {str(e)}")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. فقط اعداد (مثبت برای افزایش، منفی برای کاهش).")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
        elif state == 'waiting_for_points_adjustment':
            try:
                points = int(text.replace(',', ''))
                target_user_id = context.user_data.get('managing_points_user_id')
                if not target_user_id:
                    await update.message.reply_text("❌ کاربر یافت نشد. دوباره شروع کنید.")
                    context.user_data.clear()
                    return
                # Adjust points
                from bashgah_moshtarian.models import CustomerClubPoint
                from authentication.models import BaseUser
                from asgiref.sync import sync_to_async
                try:
                    user = await sync_to_async(BaseUser.objects.get)(id=target_user_id)
                    points_obj, created = await sync_to_async(CustomerClubPoint.objects.get_or_create)(user=user, defaults={'points': 0})
                    old_points = points_obj.points
                    new_points = old_points + points
                    if new_points < 0:
                        new_points = 0
                    await sync_to_async(points_obj.__class__.objects.filter(pk=points_obj.pk).update)(points=new_points)
                    await update.message.reply_text(f"✅ امتیازات کاربر {user.phone_number} به مبلغ {points:,} امتیاز {'افزایش' if points > 0 else 'کاهش'} یافت.\nامتیازات قبلی: {old_points:,} امتیاز\nامتیازات جدید: {new_points:,} امتیاز")
                except BaseUser.DoesNotExist:
                    await update.message.reply_text("❌ کاربر یافت نشد.")
                except Exception as e:
                    logger.error(f"Error adjusting points: {e}")
                    await update.message.reply_text(f"❌ خطا در تنظیم امتیازات: {str(e)}")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
            except ValueError:
                await update.message.reply_text("❌ امتیاز نامعتبر. فقط اعداد (مثبت برای افزایش، منفی برای کاهش).")
                context.user_data.clear()
                await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)
        elif state == 'waiting_for_reservation_search':
            search_query = text.strip()
            await ReservationManager.process_reservation_search(user_id, context, search_query)
            context.user_data.clear()
        elif context.user_data.get('subscription_step') == 'price':
            try:
                price = int(text.replace(',', ''))
                if price <= 0:
                    raise ValueError("مبلغ باید مثبت باشد")
                admin_id = context.user_data['setting_subscription_for']
                context.user_data['subscription_price'] = price
                context.user_data['subscription_step'] = 'expiry'
                await update.message.reply_text(
                    f"💰 قیمت پکیج تمدید: {price:,} تومان\n\nمرحله ۲ از ۲: تاریخ انقضای اشتراک را به فرمت YYYY-MM-DD وارد کنید:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data="cancel_subscription_setup")]]),
                    parse_mode="Markdown"
                )
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. فقط اعداد مثبت وارد کنید.")
        elif context.user_data.get('subscription_step') == 'expiry':
            from datetime import datetime
            try:
                expiry_date = datetime.fromisoformat(text.strip())
                admin_id = context.user_data['setting_subscription_for']
                price = context.user_data['subscription_price']
                
                access_data = AccessManager.load_data()
                admins = access_data['admins']
                if str(admin_id) not in admins:
                    admins[str(admin_id)] = {}
                elif isinstance(admins[str(admin_id)], str):
                    admins[str(admin_id)] = {'group': admins[str(admin_id)]}
                
                admins[str(admin_id)]['subscription_price'] = price
                admins[str(admin_id)]['subscription_expiry'] = expiry_date.isoformat()
                admins[str(admin_id)]['auto_renewal'] = True
                
                access_data['admins'] = admins
                AccessManager.save_data(access_data)
                
                await update.message.reply_text(
                    f"✅ اشتراک ادمین {admin_id} تنظیم شد:\n💰 قیمت تمدید: {price:,} تومان\n📅 تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d')}\n🔄 تمدید خودکار: فعال",
                    parse_mode="Markdown"
                )
                context.user_data.clear()
                await AdminManager.show_manage_admins(update.message.chat_id, context, admins)
            except ValueError:
                await update.message.reply_text("❌ فرمت تاریخ نامعتبر. از فرمت YYYY-MM-DD استفاده کنید (مثال: 2025-12-31).")
        elif 'setting_expiry_for' in context.user_data:
            from datetime import datetime
            try:
                expiry_str = text.strip()
                # Parse the datetime string
                expiry_date = datetime.fromisoformat(expiry_str)
                admin_id = context.user_data['setting_expiry_for']
                
                access_data = AccessManager.load_data()
                admins = access_data.get('admins', {})
                if str(admin_id) not in admins:
                    await update.message.reply_text("❌ ادمین یافت نشد!")
                    context.user_data.pop('setting_expiry_for', None)
                    return
                
                admin_data = admins[str(admin_id)]
                if isinstance(admin_data, str):
                    admin_data = {'group': admin_data}
                
                admin_data['subscription_expiry'] = expiry_date.isoformat()
                
                AccessManager.save_data(access_data)
                
                jalali_expiry = jdatetime.fromgregorian(datetime=expiry_date)
                expiry_str_jalali = jalali_expiry.strftime('%Y/%m/%d %H:%M')
                
                await update.message.reply_text(
                    f"✅ تاریخ انقضای ادمین {admin_id} تنظیم شد:\n⏰ تاریخ جدید: {expiry_str_jalali}",
                    parse_mode="Markdown"
                )
                context.user_data.pop('setting_expiry_for', None)
                await AdminManager.manage_subscription_profile(update.message.chat_id, context, admin_id)
            except ValueError:
                await update.message.reply_text("❌ فرمت تاریخ نامعتبر. از فرمت YYYY-MM-DD HH:MM استفاده کنید (مثال: 2025-12-31 23:59).")
        elif state == 'waiting_for_wallet_search':
            search_query = text.strip()
            await MenuManager.process_wallet_search(user_id, context, search_query)
            context.user_data.clear()
        # Package creation handlers
        elif 'creating_package' in context.user_data:
            processed = await AdminManager.process_package_creation(update.message.chat_id, context, text)
            if not processed:
                # If not processed by package creation, continue with other handlers
                pass
        else:
            # Default message handling for unrecognized states
            await update.message.reply_text(
                "❌ پیام نامعتبر یا وضعیت ناشناخته. لطفاً از منوی اصلی استفاده کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="go_back")]])
            )

    except Exception as e:
        logger.error(f"Error in handle_message for user {user_id}: {str(e)}")
        await update.message.reply_text(f"❌ خطایی رخ داد: {str(e)}")
        context.user_data.clear()
        await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("Bot running...")
    app.run_polling()