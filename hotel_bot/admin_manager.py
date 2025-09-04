from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SUPER_ADMINS, PERM_DISPLAY
from access_manager import AccessManager
from menu_manager import MenuManager
from receipt_manager import ReceiptManager  # برای دسترسی به load_wallets

class AdminManager:
    @staticmethod
    async def show_manage_admins(chat_id, context, admins, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
                await MenuManager.show_main_menu(user_id, context)
                return

            if not admins:
                text = "📋 **مدیریت ادمین‌ها**\n\nهیچ ادمینی وجود ندارد.\n\n**توضیح**: می‌توانید ادمین‌های جدید اضافه کنید یا گروه‌های دسترسی را مدیریت کنید."
                keyboard = [[InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin")],
                           [InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
            else:
                text = "📋 **مدیریت ادمین‌ها**\n\n**لیست ادمین‌ها**:\n"
                keyboard = []
                row = []
                for idx, uid in enumerate(admins):
                    text += f"🆔 {uid} - گروه: {admins.get(uid, 'بدون گروه')}\n"
                    row.append(InlineKeyboardButton(f"ID: {uid}", callback_data=f"view_admin:{uid}"))
                    if (idx + 1) % 2 == 0:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin")])
                keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش لیست ادمین‌ها: {str(e)}")
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_admin_details(chat_id, context, admin_id, admins, groups, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مشاهده جزئیات ادمین را ندارید!")
                await MenuManager.show_main_menu(user_id, context)
                return

            # بارگذاری پروفایل از یک فایل یا دیتابیس (فرض می‌کنیم در access_data ذخیره می‌شه)
            access_data = AccessManager.load_data()
            profile = access_data.get('profiles', {}).get(str(admin_id), {})

            group = admins.get(admin_id, "بدون گروه")
            perms = groups.get(group, set()) if group else set()
            wallets = ReceiptManager.load_wallets()
            wallet_balance = wallets.get(str(admin_id), 0)

            text = f"👤 **جزئیات ادمین**\n\n**ID**: {admin_id}\n**گروه دسترسی**: {group}\n**موجودی کیف پول**: {wallet_balance:,} تومان\n\n**مشخصات پروفایل**:\n"
            text += f"- نام: {profile.get('name', 'ندارد')}\n"
            text += f"- نام خانوادگی: {profile.get('lastname', 'ندارد')}\n"
            text += f"- کد ملی: {profile.get('national_id', 'ندارد')}\n"
            text += f"- شماره همراه: {profile.get('phone', 'ندارد')}\n"
            text += f"- شماره تلفن ثابت: {profile.get('landline', 'ندارد')}\n"
            text += f"- نام شرکت: {profile.get('company_name', 'ندارد')}\n"
            text += f"- کد ثبت شرکت: {profile.get('company_reg', 'ندارد')}\n\n"
            text += "**مجوزها**:\n"
            if perms:
                for perm in perms:
                    text += f"- **{PERM_DISPLAY[perm]['label']}**: {PERM_DISPLAY[perm]['desc']}\n"
            else:
                text += "هیچ مجوزی اختصاص نیافته.\n"
            text += "\n**توضیح**: می‌توانید گروه دسترسی این ادمین را تغییر دهید، ادمین را حذف کنید یا (در صورت سوپرادمین بودن) کیف پول و پروفایل او را مدیریت کنید."

            keyboard = [
                [InlineKeyboardButton("تغییر گروه دسترسی", callback_data=f"assign_group_menu:{admin_id}")],
                [InlineKeyboardButton("حذف ادمین", callback_data=f"delete_admin:{admin_id}")],
            ]
            if user_id in SUPER_ADMINS:
                keyboard.append([InlineKeyboardButton("💰 مشاهده موجودی", callback_data=f"view_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("🔧 تغییر موجودی", callback_data=f"modify_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("💸 شارژ کیف پول", callback_data=f"charge_admin_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("📝 ویرایش پروفایل", callback_data=f"edit_admin_profile:{admin_id}")])
            keyboard.append([InlineKeyboardButton("بازگشت به مدیریت ادمین‌ها", callback_data="manage_admins")])
            keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش جزئیات ادمین: {str(e)}")
            await MenuManager.show_main_menu(user_id, context)

        @staticmethod
        async def show_edit_admin_profile(chat_id, context, admin_id, message_id=None):
            try:
                user_id = context.user_data.get('user_id', chat_id)
                if not AccessManager.is_allowed(user_id, 'manage_admins'):
                    await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز ویرایش پروفایل ادمین را ندارید!")
                    await MenuManager.show_main_menu(user_id, context)
                    return

                access_data = AccessManager.load_data()
                profiles = access_data.setdefault('profiles', {})
                profile = profiles.setdefault(str(admin_id), {})

                # اگر تغییری در context وجود داشته باشد، پروفایل را به‌روز کن
                pending_update = context.user_data.get('pending_profile_update')
                if pending_update and pending_update.get("admin_id") == admin_id:
                    field = pending_update["field"]
                    value = pending_update["value"]
                    profile[field] = value
                    # ذخیره تغییرات در فایل/دیتابیس
                    AccessManager.save_data(access_data)
                    # بعد از اعمال تغییر، pending پاک بشه
                    context.user_data.pop('pending_profile_update', None)

                text = f"👤 **ویرایش پروفایل ادمین {admin_id}**\n\nمشخصات فعلی:\n"
                text += f"- نام: {profile.get('name', 'ندارد')}\n"
                text += f"- نام خانوادگی: {profile.get('lastname', 'ندارد')}\n"
                text += f"- کد ملی: {profile.get('national_id', 'ندارد')}\n"
                text += f"- شماره همراه: {profile.get('phone', 'ندارد')}\n"
                text += f"- شماره تلفن ثابت: {profile.get('landline', 'ندارد')}\n"
                text += f"- نام شرکت: {profile.get('company_name', 'ندارد')}\n"
                text += f"- کد ثبت شرکت: {profile.get('company_reg', 'ندارد')}\n\n"
                text += "📌 بخشی که می‌خواهید تغییر دهید را انتخاب کنید."

                keyboard = [
                    [InlineKeyboardButton("نام", callback_data=f"edit_admin_profile_field:name:{admin_id}")],
                    [InlineKeyboardButton("نام خانوادگی", callback_data=f"edit_admin_profile_field:lastname:{admin_id}")],
                    [InlineKeyboardButton("کد ملی", callback_data=f"edit_admin_profile_field:national_id:{admin_id}")],
                    [InlineKeyboardButton("شماره همراه", callback_data=f"edit_admin_profile_field:phone:{admin_id}")],
                    [InlineKeyboardButton("شماره تلفن ثابت", callback_data=f"edit_admin_profile_field:landline:{admin_id}")],
                    [InlineKeyboardButton("نام شرکت", callback_data=f"edit_admin_profile_field:company_name:{admin_id}")],
                    [InlineKeyboardButton("کد ثبت شرکت", callback_data=f"edit_admin_profile_field:company_reg:{admin_id}")],
                    [InlineKeyboardButton("بازگشت", callback_data=f"view_admin:{admin_id}")]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                if message_id:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش منوی ویرایش پروفایل ادمین: {str(e)}")
                await MenuManager.show_main_menu(user_id, context)
