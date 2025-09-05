from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SUPER_ADMINS, PERM_DISPLAY
from access_manager import AccessManager
from menu_manager import MenuManager
from receipt_manager import ReceiptManager
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminManager:
    @staticmethod
    async def show_manage_admins(chat_id, context, admins, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"نمایش لیست ادمین‌ها برای user_id: {user_id}, chat_id: {chat_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"کاربر {user_id} مجوز مدیریت ادمین‌ها رو نداره")
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
            logger.debug(f"نمایش لیست ادمین‌ها با متن: {text[:100]}... و کیبورد: {keyboard}")
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
            logger.error(f"خطا توی show_manage_admins برای user_id {user_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش لیست ادمین‌ها: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_admin_details(chat_id, context, admin_id, admins, groups, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"نمایش جزئیات ادمین برای admin_id: {admin_id}, user_id: {user_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"کاربر {user_id} مجوز مشاهده جزئیات ادمین رو نداره")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده جزئیات ادمین را ندارید!"
                )
                await MenuManager.show_main_menu(user_id, context)
                return

            group = admins.get(str(admin_id), "بدون گروه")
            perms = groups.get(group, set()) if group else set()
            wallets = ReceiptManager.load_wallets()
            logger.debug(f"کیف‌پول‌ها لود شدن: {wallets}")
            wallet_balance = wallets.get(str(admin_id), 0)

            text = (
                f"👤 **جزئیات ادمین**\n\n"
                f"**ID**: {admin_id}\n"
                f"**گروه دسترسی**: {group}\n"
                f"**موجودی کیف پول**: {wallet_balance:,} تومان\n\n"
                f"**مجوزها**:\n"
            )
            if perms:
                for perm in perms:
                    text += f"- **{PERM_DISPLAY[perm]['label']}**: {PERM_DISPLAY[perm]['desc']}\n"
            else:
                text += "هیچ مجوزی اختصاص نیافته.\n"
            text += "\n**توضیح**: می‌توانید گروه دسترسی این ادمین را تغییر دهید، ادمین را حذف کنید یا (در صورت سوپرادمین بودن) کیف پول او را مدیریت کنید."

            keyboard = [
                [InlineKeyboardButton("تغییر گروه دسترسی", callback_data=f"assign_group_menu:{admin_id}")],
                [InlineKeyboardButton("حذف ادمین", callback_data=f"delete_admin:{admin_id}")],
            ]
            if user_id in SUPER_ADMINS:
                logger.debug(f"کاربر {user_id} سوپرادمینه، اضافه کردن گزینه‌های مدیریت کیف پول برای admin_id {admin_id}")
                keyboard.append([InlineKeyboardButton("🔧 تغییر موجودی", callback_data=f"modify_wallet:{admin_id}")])
                keyboard.append([InlineKeyboardButton("💸 شارژ کیف پول", callback_data=f"charge_admin_wallet:{admin_id}")])
            keyboard.append([InlineKeyboardButton("بازگشت به مدیریت ادمین‌ها", callback_data="manage_admins")])
            keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.debug(f"نمایش جزئیات ادمین برای admin_id {admin_id} با موجودی: {wallet_balance}")
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
            logger.error(f"خطا توی show_admin_details برای admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش جزئیات ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_edit_admin_profile(chat_id, context, admin_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"نمایش ویرایش پروفایل برای admin_id: {admin_id}, user_id: {user_id}, message_id: {message_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"کاربر {user_id} مجوز ویرایش پروفایل ادمین رو نداره")
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
            logger.debug(f"نمایش ویرایش پروفایل برای admin_id {admin_id}")
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
            logger.error(f"خطا توی show_edit_admin_profile برای admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش منوی ویرایش پروفایل ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def add_admin(chat_id, context, new_id, group_name):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"اضافه کردن ادمین با new_id: {new_id}, group_name: {group_name}, user_id: {user_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"کاربر {user_id} مجوز اضافه کردن ادمین رو نداره")
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
                logger.warning(f"کاربر {new_id} قبلاً ادمین یا سوپرادمینه")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ این کاربر قبلاً ادمین یا سوپرادمین است!"
                )
                return
            if group_name not in groups:
                logger.warning(f"گروه {group_name} وجود نداره")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ گروه دسترسی انتخاب‌شده وجود ندارد!"
                )
                return

            admins[str(new_id)] = group_name
            AccessManager.save_data(access_data)
            logger.info(f"ادمین {new_id} با گروه {group_name} اضافه شد")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ ادمین با ID {new_id} با گروه {group_name} اضافه شد."
            )
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            logger.error(f"خطا توی add_admin برای new_id {new_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در افزودن ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def delete_admin(chat_id, context, admin_id):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            logger.debug(f"حذف ادمین با admin_id: {admin_id}, user_id: {user_id}")
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                logger.warning(f"کاربر {user_id} مجوز حذف ادمین رو نداره")
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
                logger.info(f"ادمین {admin_id} حذف شد")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ ادمین با ID {admin_id} حذف شد."
                )
            else:
                logger.warning(f"ادمین {admin_id} پیدا نشد")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ ادمین با ID {admin_id} یافت نشد!"
                )
            await AdminManager.show_manage_admins(chat_id, context, admins)
        except Exception as e:
            logger.error(f"خطا توی delete_admin برای admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در حذف ادمین: {str(e)}"
            )
            await MenuManager.show_main_menu(user_id, context)

# قسمت مربوط به bot.py برای هندل کردن دکمه‌ها (بدون view_wallet)
# این باید توی تابع button() توی bot.py ادغام بشه
async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    context.user_data['user_id'] = user_id
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    await query.answer()

    if not AccessManager.is_allowed(user_id):
        logger.warning(f"کاربر {user_id} دسترسی کلی نداره")
        await query.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="💢 دسترسی غیرفعال\n\nمتأسفانه شما مجاز به استفاده از خدمات این ربات نیستید."
        )
        return

    data = query.data
    access_data = AccessManager.load_data()
    admins = access_data['admins']
    groups = access_data['groups']

    try:
        # هندلرهای دیگه مثل view_admin، modify_wallet و ... اینجا می‌مونن
        # view_wallet حذف شده چون دیگه دکمه‌ای براش نداریم
        if data.startswith("view_admin:"):
            admin_id = data.split(":", 1)[1]
            await AdminManager.show_admin_details(chat_id, context, admin_id, admins, groups, message_id=message_id)
        # بقیه هندلرها (مثل modify_wallet، charge_admin_wallet و ...) باید توی bot.py باشن
        else:
            logger.warning(f"داده ناشناخته در button: {data}")
            await query.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="❌ عملیات نامعتبر!"
            )
    except Exception as e:
        logger.error(f"خطا توی button handler برای data {data}: {str(e)}", exc_info=True)
        await query.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ خطایی رخ داد: {str(e)}"
        )
        context.user_data.clear()
        await MenuManager.show_main_menu(user_id, context, message_id=message_id, chat_id=chat_id)