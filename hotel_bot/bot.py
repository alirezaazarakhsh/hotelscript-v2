import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, SUPER_ADMINS
from access_manager import AccessManager
from backup_manager import BackupManager
from file_manager import FileManager
from menu_manager import MenuManager
from admin_manager import AdminManager
from group_manager import GroupManager
from permission_manager import PermissionManager
from wallet_manager import WalletManager
from receipt_manager import ReceiptManager
from user_wallet_manager import UserWalletManager

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Handler برای دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['user_id'] = user_id
    if not AccessManager.is_allowed(user_id):
        await update.message.reply_text(
            "💢 دسترسی غیرفعال\n\n"
            "متأسفانه شما مجاز به استفاده از خدمات این ربات نیستید، در صورتی که از فعال بودن اشتراک خود مطمئن هستید، لطفاً دوباره تلاش کنید."
        )
        return
    await MenuManager.show_main_menu(user_id, context)

# Handler برای مدیریت دکمه‌ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    context.user_data['user_id'] = user_id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    await query.answer()

    if not AccessManager.is_allowed(user_id):
        await query.edit_message_text(
            "💢 دسترسی غیرفعال\n\n"
            "متأسفانه شما مجاز به استفاده از خدمات این ربات نیستید."
        )
        return

    data = query.data
    access_data = AccessManager.load_data()
    admins = access_data['admins']
    groups = access_data['groups']

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
        if data == "list_backups" and not AccessManager.is_allowed(user_id, 'list_backups'):
            await query.edit_message_text("❌ شما مجوز مشاهده لیست بکاپ‌ها را ندارید!")
            return
        if data.startswith("delete:") and not AccessManager.is_allowed(user_id, 'delete_backups'):
            await query.edit_message_text("❌ شما مجوز حذف بکاپ‌ها را ندارید!")
            return
        if data == "restore_backup" and not (AccessManager.is_allowed(user_id, 'restore_db') or AccessManager.is_allowed(user_id, 'restore_media')):
            await query.edit_message_text("❌ شما مجوز ریستور بکاپ را ندارید!")
            return
        if data == "backup_info" and not AccessManager.is_allowed(user_id, 'backup_info'):
            await query.edit_message_text("❌ شما مجوز مشاهده اطلاعات بکاپ را ندارید!")
            return
        if data == "support" and not AccessManager.is_allowed(user_id, 'support'):
            await query.edit_message_text("❌ شما مجوز دسترسی به پشتیبانی را ندارید!")
            return
        if data == "view_balance" and not AccessManager.is_allowed(user_id, 'view_balance'):
            await query.edit_message_text("❌ شما مجوز مشاهده موجودی کیف پول را ندارید!")
            return
        if data.startswith("charge_admin_wallet:") and not AccessManager.is_allowed(user_id, 'manage_wallet'):
            await query.edit_message_text("❌ شما مجوز شارژ کیف پول دیگران را ندارید!")
            return

        # Handlers
        if data == "backup_menu":
            await MenuManager.show_backup_menu(query, user_id, context)
        elif data == "backup_db":
            await BackupManager.backup_database(user_id, context)
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "backup_media":
            await BackupManager.backup_media(user_id, context)
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "list_backups":
            await show_backup_list(query, user_id, context)
        elif data.startswith("copy_name:"):
            filename = data.split(":", 1)[1]
            await context.bot.send_message(chat_id=chat_id, text=filename)
            return
        elif data.startswith("delete:"):
            await delete_backup(query, user_id, context)
        elif data == "restore_backup":
            await MenuManager.show_restore_menu(query, user_id, context)
        elif data == "backup_info":
            await MenuManager.show_backup_info(query, user_id, context)
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
            group_name = data.split(":", 1)[1]
            await GroupManager.show_group_details(chat_id, context, group_name, groups, message_id=message_id)
        elif data.startswith("view_admin:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز مشاهده ادمین را ندارید!")
                return
            admin_id = data.split(":", 1)[1]
            await AdminManager.show_admin_details(chat_id, context, admin_id, admins, groups, message_id=message_id)
        elif data.startswith("edit_group_perms:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز ویرایش گروه را ندارید!")
                return
            group_name = data.split(":", 1)[1]
            context.user_data['editing_group'] = group_name
            context.user_data['selected_perms'] = groups.get(group_name, set())
            context.user_data['state'] = 'select_group_permissions'
            await PermissionManager.show_permissions_selection(chat_id, context, group_name, is_group=True, message_id=message_id, show_desc=True)
        elif data.startswith("rename_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
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
        elif data.startswith("delete_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز حذف گروه را ندارید!")
                return
            group_name = data.split(":", 1)[1]
            if group_name in groups:
                del groups[group_name]
                AccessManager.save_data(access_data)
                await query.edit_message_text("✅ گروه با موفقیت حذف شد.")
            else:
                await query.edit_message_text("❌ گروه یافت نشد!")
            await GroupManager.show_manage_groups(chat_id, context, groups)
        elif data.startswith("delete_admin:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز حذف ادمین را ندارید!")
                return
            admin_id = data.split(":", 1)[1]
            if admin_id in admins:
                del admins[admin_id]
                AccessManager.save_data(access_data)
                await query.edit_message_text("✅ ادمین با موفقیت حذف شد.")
            else:
                await query.edit_message_text("❌ ادمین یافت نشد!")
            await AdminManager.show_manage_admins(chat_id, context, admins)
        elif data.startswith("assign_group_menu:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
                return
            admin_id = data.split(":", 1)[1]
            await PermissionManager.show_group_selection(chat_id, context, admin_id, groups, message_id=message_id)
        elif data.startswith("toggle_perm:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز تغییر مجوزها را ندارید!")
                return
            _, perm, target_type = data.split(":", 2)
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
        elif data.startswith("assign_group:"):
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await query.edit_message_text("❌ شما مجوز اختصاص گروه را ندارید!")
                return
            _, group_name, admin_id = data.split(":")
            if group_name in groups:
                admins[str(admin_id)] = group_name
                AccessManager.save_data(access_data)
                await query.edit_message_text(f"✅ گروه {group_name} با موفقیت به ادمین ID {admin_id} اختصاص یافت.")
            else:
                await query.edit_message_text(f"❌ گروه {group_name} یافت نشد!")
            context.user_data.clear()
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "cancel_perms":
            context.user_data.clear()
            await query.edit_message_text("✅ عملیات با موفقیت لغو شد.")
            await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)
        elif data == "wallet_charge":
            await WalletManager.show_wallet_menu(chat_id, context, message_id)
        elif data == "payment_gateway":
            await WalletManager.show_payment_packages(chat_id, context, message_id)
        elif data.startswith("payment:"):
            if not AccessManager.is_allowed(user_id, 'wallet_charge'):
                await query.edit_message_text("❌ شما مجوز شارژ کیف پول را ندارید!")
                return
            amount = int(data.split(":")[1])
            text = f"💸 در حال هدایت به درگاه پرداخت برای مبلغ {amount:,} تومان...\nلینک پرداخت: [لینک درگاه پرداخت - نیاز به API دارد]"
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
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
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
        elif data.startswith("confirm_receipt:"):
            if user_id in SUPER_ADMINS:
                _, u_id, amt, idx = data.split(":")
                msg = await ReceiptManager.confirm_receipt(context, int(u_id), int(amt), int(idx))
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, parse_mode="Markdown")
                await ReceiptManager.show_pending_receipts(chat_id, context)
            else:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
        elif data.startswith("reject_receipt:"):
            if user_id in SUPER_ADMINS:
                _, u_id, idx = data.split(":")
                msg = await ReceiptManager.reject_receipt(context, int(u_id), int(idx))
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, parse_mode="Markdown")
                await ReceiptManager.show_pending_receipts(chat_id, context)
            else:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ شما مجوز دسترسی ندارید!", parse_mode="Markdown")
        elif data.startswith("view_receipt:"):
            if user_id in SUPER_ADMINS:
                _, u_id, idx = data.split(":")
                receipts = ReceiptManager.load_receipts()
                if u_id in receipts and int(idx) < len(receipts[u_id]):
                    receipt = receipts[u_id][int(idx)]
                    receipt_file_id = receipt.get("receipt_file_id")
                    try:
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=receipt_file_id,
                            caption=f"رسید از کاربر {u_id} برای مبلغ {receipt['amount']:,} تومان"
                        ) if receipt_file_id.startswith("BA") else await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=receipt_file_id,
                            caption=f"رسید از کاربر {u_id} برای مبلغ {receipt['amount']:,} تومان"
                        )
                        logger.debug(f"Sent receipt file {receipt_file_id} to super admin {user_id}")
                    except Exception as e:
                        logger.error(f"Error sending receipt file to super admin {user_id}: {str(e)}")
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ خطا در نمایش فایل رسید: {str(e)}",
                            parse_mode="Markdown"
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ رسید یافت نشد!",
                        parse_mode="Markdown"
                    )
                await ReceiptManager.show_pending_receipts(chat_id, context)
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ شما مجوز دسترسی ندارید!",
                    parse_mode="Markdown"
                )
        elif data.startswith("charge_admin_wallet:"):
            admin_id = data.split(":", 1)[1]
            await UserWalletManager.prompt_for_admin_wallet_charge(chat_id, context, admin_id, message_id)

    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        await query.edit_message_text(f"❌ خطایی رخ داد: {str(e)}")
        context.user_data.clear()
        await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)

# Handler برای مدیریت پیام‌های متنی و فایل‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['user_id'] = user_id
    state = context.user_data.get('state')
    logger.debug(f"Handling message for user {user_id}, state: {state}, message type: {type(update.message).__name__}, content: {update.message}")
    text = update.message.text if update.message.text else "No text"
    data = AccessManager.load_data()
    admins = data['admins']
    groups = data['groups']

    try:
        # حالت انتظار برای دریافت ID ادمین جدید
        if state == 'waiting_for_admin_id':
            try:
                new_id = int(text)
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک ID عددی معتبر وارد کنید (فقط اعداد).")
                return
            logger.debug(f"Checking new_id: {new_id}, SUPER_ADMINS: {SUPER_ADMINS}")
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

        # حالت انتظار برای دریافت نام گروه جدید
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

        # حالت انتظار برای دریافت نام جدید گروه
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

        # حالت انتظار برای دریافت مبلغ شارژ
        elif state == 'waiting_for_amount':
            try:
                amount = int(text)
                if amount < 1000000:
                    raise ValueError("مبلغ کمتر از حداقل مجاز است")
                context.user_data['amount'] = amount
                await WalletManager.show_card_details(update.message.chat_id, context, amount)
            except ValueError:
                await update.message.reply_text("❌ مبلغ نامعتبر. حداقل ۱,۰۰۰,۰۰۰ تومان و فقط اعداد.")
                context.user_data.clear()
                await WalletManager.show_wallet_menu(update.message.chat_id, context)

        # حالت انتظار برای دریافت رسید پرداخت
        elif state == 'waiting_for_receipt':
            try:
                if not update.message:
                    logger.error(f"No message received for user {user_id} in waiting_for_receipt state")
                    await update.message.reply_text("❌ خطا: هیچ پیامی دریافت نشد!")
                    return
                
                receipt_file_id = None
                if update.message.photo:
                    receipt_file_id = update.message.photo[-1].file_id
                    logger.debug(f"Photo receipt received from user {user_id}: {receipt_file_id}")
                elif update.message.document and update.message.document.mime_type in ['application/pdf', 'image/jpeg', 'image/png']:
                    receipt_file_id = update.message.document.file_id
                    logger.debug(f"Document receipt received from user {user_id}: {receipt_file_id}")
                else:
                    logger.warning(f"Invalid file type sent by user {user_id}: {update.message.document.mime_type if update.message.document else 'No document'}")
                    await update.message.reply_text(
                        "❌ لطفاً رسید را به صورت عکس (JPEG/PNG) یا فایل PDF ارسال کنید."
                    )
                    return

                amount = context.user_data.get('amount')
                if not amount:
                    logger.error(f"No amount found in user_data for user {user_id}: {context.user_data}")
                    await update.message.reply_text(
                        "❌ خطا: مبلغ پرداخت مشخص نشده است. لطفاً دوباره شروع کنید."
                    )
                    context.user_data.clear()
                    await WalletManager.show_wallet_menu(update.message.chat_id, context)
                    return

                logger.debug(f"Calling add_receipt with user_id={user_id}, amount={amount}, receipt_file_id={receipt_file_id}")
                await ReceiptManager.add_receipt(context, user_id, amount, receipt_file_id)
                logger.info(f"Receipt successfully processed for user {user_id}")

                await update.message.reply_text(
                    "✅ رسید ارسال شد و در حال بررسی توسط ادمین است."
                )
                # ارسال اعلان به سوپرادمین‌ها
                for admin in SUPER_ADMINS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin,
                            text=f"📄 رسید جدید از کاربر {user_id} برای مبلغ {amount:,} تومان دریافت شد.",
                            parse_mode="Markdown"
                        )
                        logger.debug(f"Notified super admin {admin} for receipt from user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to notify super admin {admin}: {str(e)}")
                # ارسال فایل رسید به سوپرادمین‌ها
                for admin in SUPER_ADMINS:
                    try:
                        if update.message.photo:
                            await context.bot.send_photo(
                                chat_id=admin,
                                photo=receipt_file_id,
                                caption=f"رسید از کاربر {user_id} برای مبلغ {amount:,} تومان"
                            )
                        elif update.message.document:
                            await context.bot.send_document(
                                chat_id=admin,
                                document=receipt_file_id,
                                caption=f"رسید از کاربر {user_id} برای مبلغ {amount:,} تومان"
                            )
                        logger.debug(f"Sent receipt file to super admin {admin}")
                    except Exception as e:
                        logger.error(f"Failed to send receipt file to super admin {admin}: {str(e)}")
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Error processing receipt for user {user_id}: {str(e)}", exc_info=True)
                await update.message.reply_text(
                    f"❌ خطا در ثبت رسید: {str(e)}. لطفاً دوباره تلاش کنید."
                )
                context.user_data.clear()
                await WalletManager.show_wallet_menu(update.message.chat_id, context)

        # حالت انتظار برای دریافت مبلغ شارژ کیف پول ادمین
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
                await update.message.reply_text("❌ مبلغ نامعتبر. حداقل ۱,۰۰۰,۰۰۰ تومان و فقط اعداد.")

    except Exception as e:
        logger.error(f"Error in handle_message for user {user_id}: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ خطایی رخ داد: {str(e)}")
        context.user_data.clear()
        await MenuManager.show_main_menu(user_id, context, chat_id=update.message.chat_id)

# نمایش لیست بکاپ‌ها
async def show_backup_list(query, user_id, context):
    from config import DB_BACKUP_DIR, MEDIA_BACKUP_DIR
    if not os.path.exists(DB_BACKUP_DIR):
        os.makedirs(DB_BACKUP_DIR)
    if not os.path.exists(MEDIA_BACKUP_DIR):
        os.makedirs(MEDIA_BACKUP_DIR)

    files = []
    files.extend([f"db:{f}" for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".sql")])
    files.extend([f"media:{f}" for f in os.listdir(MEDIA_BACKUP_DIR) if f.endswith(".tar.gz")])
    files = sorted(files, key=lambda x: FileManager.get_file_datetime(x.split(":", 1)[1]), reverse=True)

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
        file_datetime = FileManager.get_file_datetime(filename)
        keyboard.append([
            InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy_name:{filename}"),
            InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}")
        ])

    keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
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

# حذف بکاپ
async def delete_backup(query, user_id, context):
    from config import DB_BACKUP_DIR, MEDIA_BACKUP_DIR
    _, file_type, filename = query.data.split(":", 2)
    backup_dir = DB_BACKUP_DIR if file_type == "db" else MEDIA_BACKUP_DIR
    file_path = os.path.join(backup_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} حذف شد.")
    else:
        await context.bot.send_message(chat_id=user_id, text=f"❌ فایل {filename} پیدا نشد!")

    files = []
    files.extend([f"db:{f}" for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".sql")])
    files.extend([f"media:{f}" for f in os.listdir(MEDIA_BACKUP_DIR) if f.endswith(".tar.gz")])
    files = sorted(files, key=lambda x: FileManager.get_file_datetime(x.split(":", 1)[1]), reverse=True)

    keyboard = []
    if files:
        for f in files:
            file_type, filename = f.split(":", 1)
            file_datetime = FileManager.get_file_datetime(filename)
            keyboard.append([
                InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy_name:{filename}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{file_type}:{filename}")
            ])
    keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
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

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ANY & ~filters.COMMAND, handle_message))  # تغییر به filters.ANY برای مدیریت عکس و سند
    logger.info("Bot running...")
    app.run_polling()