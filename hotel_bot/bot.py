from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters,  ContextTypes

from config import TOKEN
from access_manager import AccessManager
from backup_manager import BackupManager
from file_manager import FileManager
from menu_manager import MenuManager
from admin_manager import AdminManager
from group_manager import GroupManager
from permission_manager import PermissionManager

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not AccessManager.is_allowed(user_id):
        await update.message.reply_text(
            "💢 دسترسی غیرفعال\n\n"
            "متأسفانه شما مجاز به استفاده از خدمات این ربات نیستید، در صورتی که از فعال بودن اشتراک خود مطمئن هستید، لطفاً دوباره تلاش کنید."
        )
        return
    await MenuManager.show_main_menu(user_id, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not AccessManager.is_allowed(user_id, 'manage_admins'):
        await update.message.reply_text("❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
        return

    state = context.user_data.get('state')
    text = update.message.text
    data = AccessManager.load_data()
    admins = data['admins']
    groups = data['groups']

    if state == 'waiting_for_admin_id':
        try:
            new_id = str(int(text))  # حتما string
            if new_id in admins or int(new_id) in AccessManager.SUPER_ADMINS:
                await update.message.reply_text("❌ این کاربر قبلاً ادمین است!")
                return
            context.user_data['new_admin_id'] = new_id
            await PermissionManager.show_group_selection(update.message.chat_id, context, new_id, groups)
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
        await PermissionManager.show_permissions_selection(update.message.chat_id, context, group_name, is_group=True)

    elif state == 'waiting_for_new_group_name':
        new_name = text.strip()
        old_name = context.user_data.get('editing_group')
        if new_name != old_name and new_name in groups:
            await update.message.reply_text("❌ این نام گروه قبلاً وجود دارد!")
            return
        groups[new_name] = groups.pop(old_name)
        AccessManager.save_data(data)
        await update.message.reply_text(f"✅ نام گروه به {new_name} تغییر یافت.")
        context.user_data.clear()
        await GroupManager.show_manage_groups(update.message.chat_id, context)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
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
        await query.answer(f"نام فایل: {filename}", show_alert=True)
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
        await AdminManager.show_admin_details(chat_id, context, admin_id, admins, message_id=message_id)
    elif data.startswith("edit_group_perms:"):
        if not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش گروه را ندارید!")
            return
        group_name = data.split(":", 1)[1]
        context.user_data['editing_group'] = group_name
        context.user_data['selected_perms'] = groups.get(group_name, set())
        context.user_data['state'] = 'select_group_permissions'
        await PermissionManager.show_permissions_selection(chat_id, context, group_name, is_group=True, message_id=message_id, show_desc=True)
    elif data.startswith("edit_admin_perms:"):
        if not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز ویرایش ادمین را ندارید!")
            return
        admin_id = data.split(":", 1)[1]
        context.user_data['editing_admin'] = admin_id
        context.user_data['selected_perms'] = admins.get(admin_id, set())
        context.user_data['state'] = 'select_admin_permissions'
        await PermissionManager.show_permissions_selection(chat_id, context, admin_id, is_group=False, message_id=message_id, show_desc=True)
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
        await PermissionManager.show_permissions_selection(chat_id, context, target, is_group=(target_type == 'group'), message_id=message_id, show_desc=True)
    elif data.startswith("confirm_perms:"):
        if not AccessManager.is_allowed(user_id, 'manage_admins'):
            await query.edit_message_text("❌ شما مجوز تأیید مجوزها را ندارید!")
            return
        target_type = data.split(":", 1)[1]
        selected = context.user_data.get('selected_perms', set())
        if target_type == 'admin':
            admin_id = context.user_data.get('new_admin_id') or context.user_data.get('editing_admin')
            if admin_id:
                admins[str(admin_id)] = selected
                AccessManager.save_data(access_data)
                await query.edit_message_text(
                    f"✅ {'ادمین با موفقیت اضافه شد' if context.user_data.get('new_admin_id') else 'مجوزهای ادمین با موفقیت ویرایش شد'}."
                )
        elif target_type == 'group':
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
        admin_id = int(admin_id)
        if group_name in groups:
            admins[str(admin_id)] = groups[group_name].copy()
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

async def show_backup_list(query, user_id, context):
    from config import DB_BACKUP_DIR, MEDIA_BACKUP_DIR
    if not os.path.exists(DB_BACKUP_DIR):
        os.makedirs(DB_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ دیتابیس ایجاد شد.")
    if not os.path.exists(MEDIA_BACKUP_DIR):
        os.makedirs(MEDIA_BACKUP_DIR)
        await context.bot.send_message(chat_id=user_id, text="✅ دایرکتوری بکاپ مدیا ایجاد شد.")

    files = []
    files.extend([f"db:{f}" for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".sql")])
    files.extend([f"media:{f}" for f in os.listdir(MEDIA_BACKUP_DIR) if f.endswith(".tar.gz")])
    files = sorted(files, key=lambda x: FileManager.get_file_datetime(x.split(":", 1)[1]), reverse=True)

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
        file_datetime = FileManager.get_file_datetime(filename)
        row = [
            InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", 
                                callback_data=f"copy_name:{filename}"),
        ]
        if AccessManager.is_allowed(user_id, 'delete_backups'):
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

async def delete_backup(query, user_id, context):
    from config import DB_BACKUP_DIR, MEDIA_BACKUP_DIR
    _, file_type, filename = query.data.split(":", 2)
    backup_dir = DB_BACKUP_DIR if file_type == "db" else MEDIA_BACKUP_DIR
    file_path = os.path.join(backup_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        await context.bot.send_message(chat_id=user_id, text=f"✅ فایل {filename} با موفقیت حذف شد.")
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
            row = [
                InlineKeyboardButton(f"{filename} ({file_datetime}) [{file_type}]", callback_data=f"copy_name:{filename}"),
            ]
            if AccessManager.is_allowed(user_id, 'delete_backups'):
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

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling()
