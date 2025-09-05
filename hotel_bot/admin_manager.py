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

            # بارگذاری داده‌ها به‌صورت تازه
            access_data = AccessManager.load_data()  # همیشه داده‌های به‌روز رو بارگذاری می‌کنیم
            profile = access_data.get('profiles', {}).get(str(admin_id), {})

            group = admins.get(admin_id, "بدون گروه")
            perms = groups.get(group, set()) if group != "بدون گروه" else set()
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
            profile = access_data.get('profiles', {}).get(str(admin_id), {})
            
            text = f"👤 **ویرایش پروفایل ادمین {admin_id}**\n\nمشخصات فعلی:\n"
            name = profile.get('name') if profile.get('name') is not None else 'ندارد'
            lastname = profile.get('lastname') if profile.get('lastname') is not None else 'ندارد'
            national_id = profile.get('national_id') if profile.get('national_id') is not None else 'ندارد'
            phone = profile.get('phone') if profile.get('phone') is not None else 'ندارد'
            landline = profile.get('landline') if profile.get('landline') is not None else 'ندارد'
            company_name = profile.get('company_name') if profile.get('company_name') is not None else 'ندارد'
            company_reg = profile.get('company_reg') if profile.get('company_reg') is not None else 'ندارد'

            text += f"- نام: {name} (در صورت تغییر، نام جدید را وارد کنید)\n"
            text += f"- نام خانوادگی: {lastname} (در صورت تغییر، نام خانوادگی جدید را وارد کنید)\n"
            text += f"- کد ملی: {national_id} (در صورت تغییر، کد ملی جدید را وارد کنید)\n"
            text += f"- شماره همراه: {phone} (در صورت تغییر، شماره همراه جدید را وارد کنید)\n"
            text += f"- شماره تلفن ثابت: {landline} (در صورت تغییر، شماره تلفن ثابت جدید را وارد کنید)\n"
            text += f"- نام شرکت: {company_name} (در صورت تغییر، نام شرکت جدید را وارد کنید)\n"
            text += f"- کد ثبت شرکت: {company_reg} (در صورت تغییر، کد ثبت شرکت جدید را وارد کنید)\n\n"
            text += "لطفاً بخشی که می‌خواهید ویرایش کنید را انتخاب کنید. اگر تغییری نمی‌خواهید، می‌توانید همان مقدار فعلی را نگه دارید."

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
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش منوی ویرایش پروفایل ادمین: {str(e)}")
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def add_admin(chat_id, context, new_id, group_name):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز افزودن ادمین را ندارید!")
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            admins = access_data['admins']
            groups = access_data['groups']

            if str(new_id) in admins or new_id in SUPER_ADMINS:
                await context.bot.send_message(chat_id=chat_id, text="❌ این کاربر قبلاً ادمین یا سوپرادمین است!")
                return
            if group_name not in groups:
                await context.bot.send_message(chat_id=chat_id, text="❌ گروه دسترسی انتخاب‌شده وجود ندارد!")
                return

            admins[str(new_id)] = group_name
            AccessManager.save_data(access_data)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ ادمین با ID {new_id} با گروه {group_name} اضافه شد.")
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در افزودن ادمین: {str(e)}")
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def delete_admin(chat_id, context, admin_id):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز حذف ادمین را ندارید!")
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            admins = access_data['admins']

            if admin_id in admins:
                del admins[admin_id]
                AccessManager.save_data(access_data)
                await context.bot.send_message(chat_id=chat_id, text=f"✅ ادمین با ID {admin_id} حذف شد.")
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ ادمین با ID {admin_id} یافت نشد!")
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در حذف ادمین: {str(e)}")
            await MenuManager.show_main_menu(user_id, context)