from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import SUPER_ADMINS, PERM_DISPLAY
from hotel_bot.access_manager import AccessManager
from hotel_bot.menu_manager import MenuManager
from hotel_bot.receipt_manager import ReceiptManager
import logging


# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminManager:
    @staticmethod
    async def show_manage_admins(chat_id, context, admins, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"show_manage_admins called for user_id: {user_id}, chat_id: {chat_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"User {user_id} lacks manage_admins permission")
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مدیریت ادمین‌ها را ندارید!")
                await MenuManager.show_main_menu(user_id, context)
                return

            if not admins:
                text = "📋 **مدیریت ادمین‌ها**\n\nهیچ ادمینی وجود ندارد.\n\n**توضیح**: می‌توانید ادمین‌های جدید اضافه کنید یا گروه‌های دسترسی را مدیریت کنید."
                keyboard = [
                    [InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin")],
                    [InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]
                ]
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
            logger.debug(f"Displaying admin list with text: {text[:100]}... and keyboard: {keyboard}")
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
            logger.error(f"Error in show_manage_admins for user_id {user_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش لیست ادمین‌ها: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_admin_details(chat_id, context, admin_id, admins, groups, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"show_admin_details called for admin_id: {admin_id}, user_id: {user_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"User {user_id} lacks manage_admins permission")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده جزئیات ادمین را ندارید!"
                )
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            profile = access_data.get('profiles', {}).get(str(admin_id), {})
            group = admins.get(str(admin_id), "بدون گروه")
            perms = set()
            if group != "بدون گروه":
                group_perms = groups.get(group, set())
                if isinstance(group_perms, (set, list)):
                    perms = set(group_perms)
                elif isinstance(group_perms, dict):
                    # If it's a dict, get the permissions from it
                    perms = set(group_perms.get('permissions', []))
            wallets = ReceiptManager.load_wallets()
            logger.debug(f"Loaded wallets: {wallets}")
            wallet_balance = wallets.get(str(admin_id), 0)
            admin_data = access_data.get('admins', {}).get(str(admin_id), {})
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}
            license_expiry = admin_data.get('license_expiry', None)

            text = (
                f"👤 **جزئیات ادمین**\n\n"
                f"**ID**: {admin_id}\n"
                f"**گروه دسترسی**: {group}\n"
                f"**موجودی کیف پول**: {wallet_balance:,} تومان\n"
                f"**مدت زمان دسترسی**: {license_expiry if license_expiry else 'دائمی'}\n\n"
                f"**مشخصات پروفایل**:\n"
                f"- نام: {profile.get('name', 'ندارد')}\n"
                f"- نام خانوادگی: {profile.get('lastname', 'ندارد')}\n"
                f"- کد ملی: {profile.get('national_id', 'ندارد')}\n"
                f"- شماره همراه: {profile.get('phone', 'ندارد')}\n"
                f"- شماره تلفن ثابت: {profile.get('landline', 'ندارد')}\n"
                f"- نام شرکت: {profile.get('company_name', 'ندارد')}\n"
                f"- کد ثبت شرکت: {profile.get('company_reg', 'ندارد')}\n\n"
                f"**مجوزها**:\n"
            )
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
                logger.debug(f"User {user_id} is super admin, adding wallet and profile options for admin_id {admin_id}")
                keyboard.append([InlineKeyboardButton("🔧 تغییر موجودی", callback_data=f"modify_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("💸 شارژ کیف پول", callback_data=f"charge_admin_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("📝 ویرایش پروفایل", callback_data=f"edit_admin_profile:{admin_id}")])
                keyboard.append([InlineKeyboardButton("⏰ تنظیم مدت زمان", callback_data=f"set_expiry:{admin_id}")])
            keyboard.append([InlineKeyboardButton("بازگشت به مدیریت ادمین‌ها", callback_data="manage_admins")])
            keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.debug(f"Displaying admin details for admin_id {admin_id} with wallet balance: {wallet_balance}")
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
            logger.error(f"Error in show_admin_details for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش جزئیات ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_edit_admin_profile(chat_id, context, admin_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"show_edit_admin_profile called for admin_id: {admin_id}, user_id: {user_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"User {user_id} lacks manage_admins permission")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز ویرایش پروفایل ادمین را ندارید!"
                )
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            profile = access_data.get('profiles', {}).get(str(admin_id), {})
            
            text = f"👤 **ویرایش پروفایل ادمین {admin_id}**\n\nمشخصات فعلی:\n"
            name = profile.get('name', 'ندارد')
            lastname = profile.get('lastname', 'ندارد')
            national_id = profile.get('national_id', 'ندارد')
            phone = profile.get('phone', 'ندارد')
            landline = profile.get('landline', 'ندارد')
            company_name = profile.get('company_name', 'ندارد')
            company_reg = profile.get('company_reg', 'ندارد')

            text += (
                f"- نام: {name}\n"
                f"- نام خانوادگی: {lastname}\n"
                f"- کد ملی: {national_id}\n"
                f"- شماره همراه: {phone}\n"
                f"- شماره تلفن ثابت: {landline}\n"
                f"- نام شرکت: {company_name}\n"
                f"- کد ثبت شرکت: {company_reg}\n\n"
                f"لطفاً بخشی که می‌خواهید ویرایش کنید را انتخاب کنید. اگر تغییری نمی‌خواهید، می‌توانید همان مقدار فعلی را نگه دارید."
            )

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
            logger.debug(f"Displaying edit admin profile for admin_id {admin_id}")
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
            logger.error(f"Error in show_edit_admin_profile for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش منوی ویرایش پروفایل ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def add_admin(chat_id, context, new_id, group_name):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"add_admin called with new_id: {new_id}, group_name: {group_name}, user_id: {user_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"User {user_id} lacks manage_admins permission")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز افزودن ادمین را ندارید!"
                )
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            admins = access_data['admins']
            groups = access_data['groups']

            if str(new_id) in admins or new_id in SUPER_ADMINS:
                logger.warning(f"User {new_id} is already an admin or super admin")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ این کاربر قبلاً ادمین یا سوپرادمین است!"
                )
                return
            if group_name not in groups:
                logger.warning(f"Group {group_name} does not exist")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ گروه دسترسی انتخاب‌شده وجود ندارد!"
                )
                return

            admins[str(new_id)] = group_name
            AccessManager.save_data(access_data)
            logger.info(f"Admin {new_id} added with group {group_name}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ ادمین با ID {new_id} با گروه {group_name} اضافه شد."
            )
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            logger.error(f"Error in add_admin for new_id {new_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در افزودن ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def delete_admin(chat_id, context, admin_id):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"delete_admin called for admin_id: {admin_id}, user_id: {user_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"User {user_id} lacks manage_admins permission")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز حذف ادمین را ندارید!"
                )
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            admins = access_data['admins']

            if str(admin_id) in admins:
                del admins[str(admin_id)]
                AccessManager.save_data(access_data)
                logger.info(f"Admin {admin_id} deleted")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ ادمین با ID {admin_id} حذف شد."
                )
            else:
                logger.warning(f"Admin {admin_id} not found")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ ادمین با ID {admin_id} یافت نشد!"
                )
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            logger.error(f"Error in delete_admin for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در حذف ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)