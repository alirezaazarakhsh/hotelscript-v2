from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import SUPER_ADMINS, PERMISSIONS, PERM_DISPLAY
from hotel_bot.access_manager import AccessManager
from hotel_bot.receipt_manager import ReceiptManager
import logging
import time
from datetime import datetime


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
                from hotel_bot.menu_manager import MenuManager
                await MenuManager.show_main_menu(user_id, context)
                return

            if not admins:
                text = f"📋 **مدیریت ادمین‌ها**\n\nهیچ ادمینی وجود ندارد.\n\n**توضیح**: می‌توانید ادمین‌های جدید اضافه کنید یا گروه‌های دسترسی را مدیریت کنید.\n\n_آخرین بروزرسانی: {int(time.time())}_"
                keyboard = [
                    [InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="add_admin")],
                    [InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]
                ]
            else:
                text = "📋 **مدیریت ادمین‌ها**\n\n**لیست ادمین‌ها**:\n"
                keyboard = []
                row = []
                for idx, uid in enumerate(admins):
                    admin_info = admins.get(uid, {})
                    if isinstance(admin_info, str):
                        group_name = admin_info
                    elif isinstance(admin_info, dict):
                        group_name = admin_info.get('group', 'بدون گروه')
                    else:
                        group_name = 'بدون گروه'
                    text += f"🆔 {uid} - گروه: {group_name}\n"
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
            from hotel_bot.menu_manager import MenuManager
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
                from hotel_bot.menu_manager import MenuManager
                await MenuManager.show_main_menu(user_id, context)
                return

            access_data = AccessManager.load_data()
            profile = access_data.get('profiles', {}).get(str(admin_id), {})
            # Ensure profile is a dict
            if not isinstance(profile, dict):
                profile = {}
            admin_data = access_data.get('admins', {}).get(str(admin_id), {})
            # Ensure admin_data is a dict
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}
            elif not isinstance(admin_data, dict):
                admin_data = {}
            group = admin_data.get('group', "بدون گروه")
            perms = set()
            if group != "بدون گروه":
                group_perms = groups.get(group, set())
                # Ensure group_perms is a set or list
                if not isinstance(group_perms, (set, list, dict)):
                    group_perms = set()
                logger.debug(f"Group perms for {group}: {group_perms}, type: {type(group_perms)}")
                if isinstance(group_perms, (set, list)):
                    # Filter out any non-string items to ensure hashability
                    perms = set(item for item in group_perms if isinstance(item, str))
                elif isinstance(group_perms, dict):
                    # If it's a dict, get the permissions from it
                    perm_list = group_perms.get('permissions', [])
                    logger.debug(f"Perm list from dict: {perm_list}, type: {type(perm_list)}")
                    if isinstance(perm_list, (set, list)):
                        # Filter out any non-string items to ensure hashability
                        perms = set(item for item in perm_list if isinstance(item, str))
                    else:
                        perms = set()  # Fallback to empty set
                else:
                    perms = set()  # Fallback to empty set
            logger.debug(f"Final perms: {perms}, type: {type(perms)}")
            wallets = ReceiptManager.load_wallets()
            logger.debug(f"Loaded wallets: {wallets}")
            wallet_balance = wallets.get(str(admin_id), 0)
            admin_data = access_data.get('admins', {}).get(str(admin_id), {})
            # Ensure admin_data is a dict
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}
            elif not isinstance(admin_data, dict):
                admin_data = {}
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
                    if isinstance(perm, str) and perm in PERM_DISPLAY:
                        text += f"- **{PERM_DISPLAY[perm]['label']}**: {PERM_DISPLAY[perm]['desc']}\n"
                    else:
                        logger.warning(f"Invalid permission found: {perm} (type: {type(perm)})")
                        # Skip invalid permissions
                        continue
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
                keyboard.append([InlineKeyboardButton("📊 پروفایل اشتراک", callback_data=f"view_subscription:{admin_id}")])
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

    @staticmethod
    async def show_subscription_profile(chat_id, context, admin_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده پروفایل اشتراک را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            admin_data = access_data.get('admins', {}).get(str(admin_id), {})
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}

            subscription_price = admin_data.get('subscription_price', 0)
            subscription_expiry = admin_data.get('subscription_expiry')
            auto_renewal = admin_data.get('auto_renewal', False)

            from datetime import datetime
            days_remaining = 0
            status = "❌ تنظیم نشده"
            
            if subscription_expiry:
                try:
                    expiry = datetime.fromisoformat(subscription_expiry)
                    now = datetime.now()
                    if expiry > now:
                        days_remaining = (expiry - now).days
                        if days_remaining > 30:
                            status = "✅ فعال"
                        elif days_remaining > 7:
                            status = "⚠️ نیاز به تمدید"
                        else:
                            status = "🔴 منقضی شدن نزدیک"
                    else:
                        status = "❌ منقضی شده"
                        days_remaining = (now - expiry).days
                except ValueError:
                    status = "❌ تاریخ نامعتبر"

            text = (
                f"📊 **پروفایل اشتراک ادمین {admin_id}**\n\n"
                f"**وضعیت اشتراک**: {status}\n"
                f"**مبلغ تمدید**: {subscription_price:,} تومان\n"
                f"**تاریخ انقضا**: {subscription_expiry if subscription_expiry else 'تنظیم نشده'}\n"
                f"**روزهای باقی‌مانده**: {days_remaining if subscription_expiry else 'N/A'}\n"
                f"**تمدید خودکار**: {'✅ فعال' if auto_renewal else '❌ غیرفعال'}\n\n"
            )

            if auto_renewal and subscription_price > 0:
                wallets = ReceiptManager.load_wallets()
                wallet_balance = wallets.get(str(admin_id), 0)
                text += f"**موجودی کیف پول**: {wallet_balance:,} تومان\n"
                if wallet_balance >= subscription_price:
                    text += "💚 **وضعیت تمدید**: آماده تمدید\n"
                else:
                    text += "💔 **وضعیت تمدید**: موجودی کافی نیست\n"

            keyboard = [
                [InlineKeyboardButton("🔄 تمدید ماهانه", callback_data=f"renew_monthly:{admin_id}")],
                [InlineKeyboardButton("🔄 تمدید سالانه", callback_data=f"renew_yearly:{admin_id}")],
                [InlineKeyboardButton("بازگشت به جزئیات ادمین", callback_data=f"view_admin:{admin_id}")]
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
            logger.error(f"Error in show_subscription_profile for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش پروفایل اشتراک: {str(e)}"
            )

    @staticmethod
    def check_and_auto_renew_subscriptions():
        """بررسی و تمدید خودکار اشتراک‌های منقضی شده"""
        try:
            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            wallets = ReceiptManager.load_wallets()
            
            renewed_count = 0
            for admin_id, admin_data in admins.items():
                if isinstance(admin_data, str):
                    continue
                
                if not admin_data.get('auto_renewal', False):
                    continue
                
                subscription_expiry = admin_data.get('subscription_expiry')
                subscription_price = admin_data.get('subscription_price', 0)
                
                if not subscription_expiry or subscription_price <= 0:
                    continue
                
                from datetime import datetime, timedelta
                try:
                    expiry = datetime.fromisoformat(subscription_expiry)
                    now = datetime.now()
                    
                    # اگر اشتراک منقضی شده یا کمتر از 3 روز باقی مانده
                    if expiry <= now + timedelta(days=3):
                        wallet_balance = wallets.get(str(admin_id), 0)
                        
                        if wallet_balance >= subscription_price:
                            # تمدید اشتراک
                            new_expiry = expiry + timedelta(days=30)  # تمدید ماهانه
                            admin_data['subscription_expiry'] = new_expiry.isoformat()
                            
                            # کسر از کیف پول
                            wallets[str(admin_id)] = wallet_balance - subscription_price
                            
                            renewed_count += 1
                            logger.info(f"Auto-renewed subscription for admin {admin_id}")
                        else:
                            logger.warning(f"Insufficient balance for auto-renewal of admin {admin_id}")
                except ValueError:
                    logger.error(f"Invalid subscription expiry date for admin {admin_id}: {subscription_expiry}")
            
            if renewed_count > 0:
                access_data['admins'] = admins
                AccessManager.save_data(access_data)
                ReceiptManager.save_wallets(wallets)
                
                # ارسال اعلان به سوپر ادمین‌ها
                notification_text = f"🔄 **تمدید خودکار اشتراک**\n\n{renewed_count} اشتراک به صورت خودکار تمدید شد."
                for super_admin in SUPER_ADMINS:
                    try:
                        # ارسال اعلان (این قسمت نیاز به context دارد، بعداً پیاده‌سازی می‌شود)
                        logger.info(f"Auto-renewed {renewed_count} subscriptions")
                    except Exception as e:
                        logger.error(f"Failed to send renewal notification to {super_admin}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in check_and_auto_renew_subscriptions: {str(e)}")

    @staticmethod
    def send_subscription_reminders(context):
        """ارسال یادآوری برای تمدید اشتراک"""
        try:
            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            
            for admin_id, admin_data in admins.items():
                if isinstance(admin_data, str):
                    continue
                
                subscription_expiry = admin_data.get('subscription_expiry')
                if not subscription_expiry:
                    continue
                
                from datetime import datetime, timedelta
                try:
                    expiry = datetime.fromisoformat(subscription_expiry)
                    now = datetime.now()
                    days_remaining = (expiry - now).days
                    
                    # ارسال یادآوری اگر کمتر از 7 روز باقی مانده
                    if 0 < days_remaining <= 7:
                        message = (
                            f"⚠️ **یادآوری تمدید اشتراک**\n\n"
                            f"اشتراک شما {days_remaining} روز دیگر منقضی می‌شود.\n"
                            f"برای جلوگیری از قطع سرویس، لطفاً اشتراک خود را تمدید کنید."
                        )
                        
                        try:
                            # ارسال یادآوری (این قسمت نیاز به context دارد، بعداً پیاده‌سازی می‌شود)
                            logger.info(f"Subscription reminder sent to admin {admin_id}: {days_remaining} days remaining")
                        except Exception as e:
                            logger.error(f"Failed to send reminder to admin {admin_id}: {e}")
                            
                except ValueError:
                    logger.error(f"Invalid subscription expiry date for admin {admin_id}: {subscription_expiry}")
                    
        except Exception as e:
            logger.error(f"Error in send_subscription_reminders: {str(e)}")

    @staticmethod
    async def show_subscription_management(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مدیریت اشتراک‌ها را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            
            if not packages:
                text = f"📦 **مدیریت پکیج‌های اشتراک**\n\nهیچ پکیج اشتراکی وجود ندارد.\n\n**توضیح**: پکیج‌های اشتراک شامل سطوح مختلف دسترسی و خدمات هستند.\n\n_آخرین بروزرسانی: {int(time.time())}_"
                keyboard = [
                    [InlineKeyboardButton("➕ ایجاد پکیج جدید", callback_data="create_new_package")],
                    [InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]
                ]
            else:
                text = "📦 **مدیریت پکیج‌های اشتراک**\n\n**پکیج‌های موجود**:\n"
                keyboard = []
                row = []
                for package_id, package in packages.items():
                    package_group = package.get('group', 'نامشخص')
                    group_count = len(access_data.get('groups', {}).get(package_group, set())) if package_group in access_data.get('groups', {}) else 0
                    text += f"📋 {package.get('name', package_id)} - {package.get('price', 0):,} تومان (گروه: {package_group}, {group_count} مجوز)\n"
                    row.append(InlineKeyboardButton(package.get('name', package_id), callback_data=f"package_details:{package_id}"))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("➕ ایجاد پکیج جدید", callback_data="create_new_package")])
                keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

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
            logger.error(f"Error in show_subscription_management: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش مدیریت اشتراک‌ها: {str(e)}"
            )

    @staticmethod
    async def show_package_details(chat_id, context, package_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده پکیج اشتراک را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            
            if package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            package = packages[package_id]
            package_group = package.get('group')
            
            text = f"📋 **پکیج: {package.get('name', package_id)}**\n\n"
            text += f"💰 **قیمت**: {package.get('price', 0):,} تومان\n"
            text += f"⏱️ **مدت**: {package.get('duration_days', 30)} روز\n"
            text += f"👥 **گروه دسترسی**: {package_group or 'نامشخص'}\n"
            text += f"📝 **توضیحات**: {package.get('description', 'ندارد')}\n\n"
            
            # نمایش دسترسی‌های گروه
            if package_group and package_group in access_data.get('groups', {}):
                group_permissions = access_data['groups'][package_group]
                if group_permissions:
                    text += "**مجوزهای گروه**:\n"
                    for perm in group_permissions:
                        if perm in PERM_DISPLAY:
                            text += f"✅ {PERM_DISPLAY[perm]['label']}\n"
                        else:
                            text += f"✅ {perm}\n"
                else:
                    text += "❌ گروه هیچ مجوزی ندارد.\n"
            else:
                text += "❌ گروه دسترسی یافت نشد.\n"
            
            text += "\n**توضیح**: می‌توانید این پکیج را ویرایش، حذف یا به ادمین‌ها اختصاص دهید."

            keyboard = [
                [InlineKeyboardButton("✏️ ویرایش پکیج", callback_data=f"edit_package:{package_id}")],
                [InlineKeyboardButton("🗑️ حذف پکیج", callback_data=f"delete_package:{package_id}")],
                [InlineKeyboardButton("👥 اختصاص به ادمین", callback_data=f"assign_package:{package_id}")],
                [InlineKeyboardButton("⬆️ ارتقا پکیج", callback_data=f"upgrade_package:{package_id}")],
                [InlineKeyboardButton("بازگشت به مدیریت اشتراک‌ها", callback_data="manage_subscriptions")]
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
            logger.error(f"Error in show_package_details for package {package_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش جزئیات پکیج: {str(e)}"
            )

    @staticmethod
    async def create_new_package(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز ایجاد پکیج اشتراک را ندارید!"
                )
                return

            text = "📦 **ایجاد پکیج اشتراک جدید**\n\n"
            text += "لطفاً اطلاعات پکیج را مرحله به مرحله وارد کنید:\n\n"
            text += "1️⃣ ابتدا نام پکیج را ارسال کنید (مثال: پکیج طلایی)"

            context.user_data['creating_package'] = {
                'step': 'name',
                'data': {}
            }

            keyboard = [
                [InlineKeyboardButton("❌ لغو", callback_data="cancel_create_package")]
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
            logger.error(f"Error in create_new_package: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در ایجاد پکیج جدید: {str(e)}"
            )

    @staticmethod
    async def process_package_creation(chat_id, context, user_input):
        try:
            if 'creating_package' not in context.user_data:
                return False

            package_data = context.user_data['creating_package']
            step = package_data['step']

            if step == 'name':
                if len(user_input.strip()) < 2:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ نام پکیج باید حداقل ۲ کاراکتر باشد. لطفاً دوباره امتحان کنید:"
                    )
                    return True

                package_data['data']['name'] = user_input.strip()
                package_data['step'] = 'price'
                
                text = "2️⃣ قیمت پکیج را به تومان وارد کنید (فقط عدد):\n"
                text += "مثال: 50000"
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                return True

            elif step == 'price':
                try:
                    price = int(user_input.strip())
                    if price <= 0:
                        raise ValueError("قیمت باید مثبت باشد")
                    
                    package_data['data']['price'] = price
                    package_data['step'] = 'duration'
                    
                    text = "3️⃣ مدت زمان پکیج را به روز وارد کنید:\n"
                    text += "مثال: 30 (برای یک ماه)"
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text
                    )
                    return True
                except ValueError:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ قیمت باید یک عدد مثبت باشد. لطفاً دوباره امتحان کنید:"
                    )
                    return True

            elif step == 'duration':
                try:
                    duration = int(user_input.strip())
                    if duration <= 0:
                        raise ValueError("مدت زمان باید مثبت باشد")
                    
                    package_data['data']['duration_days'] = duration
                    package_data['step'] = 'description'
                    
                    text = "4️⃣ توضیحات پکیج را وارد کنید (اختیاری):\n"
                    text += "می‌توانید توضیحات را خالی بگذارید یا توضیحات مفیدی بنویسید."
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text
                    )
                    return True
                except ValueError:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ مدت زمان باید یک عدد مثبت باشد. لطفاً دوباره امتحان کنید:"
                    )
                    return True

            elif step == 'description':
                package_data['data']['description'] = user_input.strip() if user_input.strip() else ""
                package_data['step'] = 'group_selection'
                
                # نمایش لیست گروه‌های دسترسی برای انتخاب
                access_data = AccessManager.load_data()
                groups = access_data.get('groups', {})
                
                if not groups:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ هیچ گروه دسترسی‌ای وجود ندارد. لطفاً ابتدا گروه‌های دسترسی را ایجاد کنید.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="cancel_create_package")]])
                    )
                    return True
                
                text = "5️⃣ گروه دسترسی پکیج را انتخاب کنید:\n\n"
                text += "**گروه‌های دسترسی موجود**:\n"
                
                keyboard = []
                for group_name, permissions in groups.items():
                    perm_count = len(permissions) if isinstance(permissions, set) else 0
                    text += f"• {group_name}: {perm_count} مجوز\n"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"انتخاب {group_name}", 
                            callback_data=f"select_package_group:{group_name}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("❌ لغو", callback_data="cancel_create_package")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                return True

            return False
        except Exception as e:
            logger.error(f"Error in process_package_creation: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در پردازش ایجاد پکیج: {str(e)}"
            )
            return False

    @staticmethod
    async def select_package_group(chat_id, context, group_name, message_id=None):
        try:
            if 'creating_package' not in context.user_data:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ اطلاعات ایجاد پکیج یافت نشد!"
                )
                return

            # بررسی وجود گروه
            access_data = AccessManager.load_data()
            groups = access_data.get('groups', {})
            if group_name not in groups:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ گروه دسترسی یافت نشد!"
                )
                return

            # ذخیره گروه انتخاب شده
            context.user_data['creating_package']['data']['group'] = group_name
            
            # تکمیل ایجاد پکیج
            await AdminManager.finish_package_creation(chat_id, context)
            
        except Exception as e:
            logger.error(f"Error in select_package_group: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در انتخاب گروه: {str(e)}"
            )

    @staticmethod
    async def finish_package_creation(chat_id, context):
        try:
            if 'creating_package' not in context.user_data:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ اطلاعات ایجاد پکیج یافت نشد!"
                )
                return

            package_data = context.user_data['creating_package']['data']
            group_name = package_data.get('group')

            if not group_name:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ گروه دسترسی انتخاب نشده!"
                )
                return

            # تولید ID منحصر به فرد برای پکیج
            package_id = f"package_{int(time.time())}_{chat_id}"

            # ذخیره پکیج جدید
            access_data = AccessManager.load_data()
            if 'subscription_packages' not in access_data:
                access_data['subscription_packages'] = {}
            
            access_data['subscription_packages'][package_id] = {
                'name': package_data['name'],
                'price': package_data['price'],
                'duration_days': package_data['duration_days'],
                'description': package_data.get('description', ''),
                'group': group_name,
                'created_by': context.user_data.get('user_id', chat_id),
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }

            AccessManager.save_data(access_data)

            # پاک کردن داده‌های موقت
            del context.user_data['creating_package']

            # دریافت اطلاعات گروه
            groups = access_data.get('groups', {})
            group_permissions = groups.get(group_name, set())
            perm_count = len(group_permissions) if isinstance(group_permissions, set) else 0

            text = f"✅ **پکیج '{package_data['name']}' با موفقیت ایجاد شد!**\n\n"
            text += f"📋 **شناسه پکیج**: {package_id}\n"
            text += f"💰 **قیمت**: {package_data['price']:,} تومان\n"
            text += f"⏱️ **مدت**: {package_data['duration_days']} روز\n"
            text += f"👥 **گروه دسترسی**: {group_name} ({perm_count} مجوز)\n\n"
            text += "اکنون می‌توانید این پکیج را به ادمین‌ها اختصاص دهید."

            keyboard = [
                [InlineKeyboardButton("👥 اختصاص به ادمین", callback_data=f"assign_package:{package_id}")],
                [InlineKeyboardButton("📦 مشاهده همه پکیج‌ها", callback_data="manage_subscriptions")],
                [InlineKeyboardButton("➕ ایجاد پکیج جدید", callback_data="create_new_package")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error in finish_package_creation: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تکمیل ایجاد پکیج: {str(e)}"
            )

    @staticmethod
    async def assign_package_to_admin(chat_id, context, package_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز اختصاص پکیج را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            
            if package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            package = packages[package_id]
            admins = access_data.get('admins', {})

            if not admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ هیچ ادمینی یافت نشد!"
                )
                return

            text = f"👥 **اختصاص پکیج '{package.get('name', package_id)}' به ادمین**\n\n"
            text += "لطفاً ادمینی را برای اختصاص این پکیج انتخاب کنید:\n\n"

            keyboard = []
            for admin_id, admin_data in admins.items():
                admin_name = admin_data.get('name', f'ادمین {admin_id}')
                current_package = admin_data.get('subscription_package')
                
                if current_package:
                    status = f" (پکیج فعلی: {packages.get(current_package, {}).get('name', 'نامشخص')})"
                else:
                    status = " (بدون پکیج)"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{admin_name}{status}", 
                        callback_data=f"confirm_assign:{package_id}:{admin_id}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("بازگشت به جزئیات پکیج", callback_data=f"package_details:{package_id}")
            ])

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
            logger.error(f"Error in assign_package_to_admin for package {package_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در اختصاص پکیج: {str(e)}"
            )

    @staticmethod
    async def confirm_package_assignment(chat_id, context, package_id, admin_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز اختصاص پکیج را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            admins = access_data.get('admins', {})

            if package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            if admin_id not in admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ ادمین یافت نشد!"
                )
                return

            package = packages[package_id]
            admin_data = admins[admin_id]

            # محاسبه تاریخ انقضا
            duration_days = package.get('duration_days', 30)
            expiry_date = datetime.now() + timedelta(days=duration_days)

            # اختصاص پکیج به ادمین
            admin_data['subscription_package'] = package_id
            admin_data['subscription_expiry'] = expiry_date.isoformat()
            admin_data['subscription_assigned_by'] = user_id
            admin_data['subscription_assigned_at'] = datetime.now().isoformat()

            # دسترسی‌ها اکنون از گروه پکیج گرفته می‌شود، نیازی به کپی نیست
            # admin_data['permissions'] = package.get('permissions', [])

            AccessManager.save_data(access_data)

            # دریافت اطلاعات گروه پکیج
            package_group = package.get('group')
            groups = access_data.get('groups', {})
            group_permissions = groups.get(package_group, set()) if package_group else set()
            perm_count = len(group_permissions) if isinstance(group_permissions, set) else 0

            text = f"✅ **پکیج با موفقیت اختصاص یافت!**\n\n"
            text += f"👤 **ادمین**: {admin_data.get('name', f'ادمین {admin_id}')}\n"
            text += f"📦 **پکیج**: {package.get('name', package_id)}\n"
            text += f"👥 **گروه دسترسی**: {package_group or 'نامشخص'}\n"
            text += f"⏰ **تاریخ انقضا**: {expiry_date.strftime('%Y/%m/%d %H:%M')}\n"
            text += f"🔐 **مجوزها**: {perm_count} مورد\n\n"
            text += "ادمین اکنون می‌تواند از امکانات پکیج استفاده کند."

            keyboard = [
                [InlineKeyboardButton("👥 اختصاص پکیج دیگر", callback_data=f"assign_package:{package_id}")],
                [InlineKeyboardButton("📊 مشاهده وضعیت اشتراک‌ها", callback_data="view_subscription_status")],
                [InlineKeyboardButton("بازگشت به مدیریت اشتراک‌ها", callback_data="manage_subscriptions")]
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
            logger.error(f"Error in confirm_package_assignment for package {package_id} and admin {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تأیید اختصاص پکیج: {str(e)}"
            )

    @staticmethod
    async def view_subscription_status(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده وضعیت اشتراک‌ها را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            packages = access_data.get('subscription_packages', {})

            if not admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ هیچ ادمینی یافت نشد!"
                )
                return

            text = "📊 **وضعیت اشتراک‌های ادمین‌ها**\n\n"

            active_count = 0
            expired_count = 0
            no_package_count = 0

            for admin_id, admin_data in admins.items():
                admin_name = admin_data.get('name', f'ادمین {admin_id}')
                package_id = admin_data.get('subscription_package')
                expiry_str = admin_data.get('subscription_expiry')

                if package_id and package_id in packages:
                    package = packages[package_id]
                    package_name = package.get('name', package_id)
                    
                    if expiry_str:
                        try:
                            expiry_date = datetime.fromisoformat(expiry_str)
                            now = datetime.now()
                            
                            if expiry_date > now:
                                status = "🟢 فعال"
                                active_count += 1
                                days_left = (expiry_date - now).days
                                expiry_info = f"انقضا: {expiry_date.strftime('%Y/%m/%d')} ({days_left} روز مانده)"
                            else:
                                status = "🔴 منقضی"
                                expired_count += 1
                                days_expired = (now - expiry_date).days
                                expiry_info = f"منقضی شده: {days_expired} روز پیش"
                        except:
                            status = "⚠️ خطا در تاریخ"
                            expiry_info = "تاریخ نامعتبر"
                    else:
                        status = "🟡 بدون تاریخ انقضا"
                        expiry_info = "تاریخ انقضا تنظیم نشده"
                else:
                    status = "⚫ بدون پکیج"
                    package_name = "ندارد"
                    expiry_info = "-"
                    no_package_count += 1

                text += f"👤 **{admin_name}**\n"
                text += f"📦 پکیج: {package_name}\n"
                text += f"📅 {expiry_info}\n"
                text += f"📊 وضعیت: {status}\n\n"

            text += f"📈 **آمار کلی**:\n"
            text += f"🟢 فعال: {active_count}\n"
            text += f"🔴 منقضی: {expired_count}\n"
            text += f"⚫ بدون پکیج: {no_package_count}\n"
            text += f"👥 مجموع ادمین‌ها: {len(admins)}"

            keyboard = [
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="view_subscription_status")],
                [InlineKeyboardButton("📦 مدیریت پکیج‌ها", callback_data="manage_subscriptions")],
                [InlineKeyboardButton("👥 اختصاص پکیج", callback_data="assign_package_menu")]
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
            logger.error(f"Error in view_subscription_status: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش وضعیت اشتراک‌ها: {str(e)}"
            )

    @staticmethod
    async def upgrade_admin_package(chat_id, context, admin_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز ارتقای پکیج را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            packages = access_data.get('subscription_packages', {})

            if admin_id not in admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ ادمین یافت نشد!"
                )
                return

            admin_data = admins[admin_id]
            current_package_id = admin_data.get('subscription_package')

            text = f"⬆️ **ارتقای پکیج ادمین: {admin_data.get('name', f'ادمین {admin_id}')}**\n\n"

            if current_package_id and current_package_id in packages:
                current_package = packages[current_package_id]
                text += f"📦 **پکیج فعلی**: {current_package.get('name', current_package_id)}\n"
                text += f"💰 **قیمت فعلی**: {current_package.get('price', 0):,} تومان\n\n"
            else:
                text += "📦 **پکیج فعلی**: ندارد\n\n"

            text += "پکیج جدیدی برای ارتقا انتخاب کنید:\n\n"

            keyboard = []
            for package_id, package in packages.items():
                if package_id != current_package_id:  # نمایش پکیج‌های دیگر
                    package_name = package.get('name', package_id)
                    price = package.get('price', 0)
                    duration = package.get('duration_days', 30)
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{package_name} - {price:,} تومان ({duration} روز)", 
                            callback_data=f"confirm_upgrade:{admin_id}:{package_id}"
                        )
                    ])

            if not keyboard:
                text += "❌ هیچ پکیج دیگری موجود نیست!"
                keyboard = [[InlineKeyboardButton("بازگشت", callback_data="view_subscription_status")]]
            else:
                keyboard.append([
                    InlineKeyboardButton("بازگشت به وضعیت اشتراک‌ها", callback_data="view_subscription_status")
                ])

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
            logger.error(f"Error in upgrade_admin_package for admin {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در ارتقای پکیج: {str(e)}"
            )

    @staticmethod
    async def confirm_package_upgrade(chat_id, context, admin_id, new_package_id, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_subscriptions'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز ارتقای پکیج را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            packages = access_data.get('subscription_packages', {})

            if admin_id not in admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ ادمین یافت نشد!"
                )
                return

            if new_package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج جدید یافت نشد!"
                )
                return

            admin_data = admins[admin_id]
            new_package = packages[new_package_id]
            old_package_id = admin_data.get('subscription_package')

            # محاسبه تاریخ انقضا جدید
            duration_days = new_package.get('duration_days', 30)
            new_expiry_date = datetime.now() + timedelta(days=duration_days)

            # بروزرسانی اطلاعات ادمین
            admin_data['subscription_package'] = new_package_id
            admin_data['subscription_expiry'] = new_expiry_date.isoformat()
            admin_data['subscription_upgraded_by'] = user_id
            admin_data['subscription_upgraded_at'] = datetime.now().isoformat()
            admin_data['previous_package'] = old_package_id

            # دسترسی‌ها اکنون از گروه پکیج گرفته می‌شود
            # admin_data['permissions'] = new_package.get('permissions', [])

            AccessManager.save_data(access_data)

            AccessManager.save_data(access_data)

            text = f"✅ **پکیج ادمین با موفقیت ارتقا یافت!**\n\n"
            text += f"👤 **ادمین**: {admin_data.get('name', f'ادمین {admin_id}')}\n"
            
            if old_package_id and old_package_id in packages:
                old_package = packages[old_package_id]
                text += f"📦 **پکیج قدیمی**: {old_package.get('name', old_package_id)}\n"
            
            text += f"⬆️ **پکیج جدید**: {new_package.get('name', new_package_id)}\n"
            text += f"💰 **قیمت جدید**: {new_package.get('price', 0):,} تومان\n"
            text += f"⏰ **تاریخ انقضا جدید**: {new_expiry_date.strftime('%Y/%m/%d %H:%M')}\n"
            text += f"🔐 **مجوزهای جدید**: {len(new_package.get('permissions', []))} مورد\n\n"
            text += "ادمین اکنون از امکانات پکیج جدید برخوردار است."

            keyboard = [
                [InlineKeyboardButton("⬆️ ارتقای ادمین دیگر", callback_data="upgrade_package_menu")],
                [InlineKeyboardButton("📊 مشاهده وضعیت اشتراک‌ها", callback_data="view_subscription_status")],
                [InlineKeyboardButton("بازگشت به مدیریت اشتراک‌ها", callback_data="manage_subscriptions")]
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
            logger.error(f"Error in confirm_package_upgrade for admin {admin_id} to package {new_package_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تأیید ارتقای پکیج: {str(e)}"
            )

    @staticmethod
    def check_subscription_status(user_id):
        """
        بررسی وضعیت اشتراک کاربر
        بازگرداندن: (is_active, package_info, days_left)
        """
        try:
            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            packages = access_data.get('subscription_packages', {})

            if str(user_id) not in admins:
                return False, None, 0

            admin_data = admins[str(user_id)]
            package_id = admin_data.get('subscription_package')
            expiry_str = admin_data.get('subscription_expiry')

            if not package_id or package_id not in packages:
                return False, None, 0

            package = packages[package_id]

            if not expiry_str:
                return False, package, 0

            try:
                expiry_date = datetime.fromisoformat(expiry_str)
                now = datetime.now()
                
                if expiry_date > now:
                    days_left = (expiry_date - now).days
                    return True, package, days_left
                else:
                    return False, package, 0
            except:
                return False, package, 0

        except Exception as e:
            logger.error(f"Error in check_subscription_status for user {user_id}: {str(e)}", exc_info=True)
            return False, None, 0

    @staticmethod
    async def show_user_subscription_status(chat_id, context, message_id=None):
        """
        نمایش وضعیت اشتراک برای کاربر فعلی
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            is_active, package, days_left = AdminManager.check_subscription_status(user_id)
            
            if not package:
                from datetime import datetime
                text = f"📊 **وضعیت اشتراک شما**\n\n"
                text += "❌ **شما هیچ پکیج اشتراکی ندارید**\n\n"
                text += f"برای دسترسی به امکانات کامل، لطفاً با مدیریت تماس بگیرید.\n\n"
                text += f"_آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
                
                keyboard = [
                    [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")],
                    [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="contact_support")],
                    [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="go_back")]
                ]
            else:
                package_name = package.get('name', 'نامشخص')
                price = package.get('price', 0)
                duration = package.get('duration_days', 30)
                package_group = package.get('group')
                
                text = f"📊 **وضعیت اشتراک شما**\n\n"
                text += f"📦 **پکیج**: {package_name}\n"
                text += f"💰 **قیمت**: {price:,} تومان\n"
                text += f"⏱️ **مدت**: {duration} روز\n"
                text += f"👥 **گروه دسترسی**: {package_group or 'نامشخص'}\n"
                
                if is_active:
                    text += f"🟢 **وضعیت**: فعال\n"
                    text += f"📅 **روزهای باقی‌مانده**: {days_left} روز\n"
                else:
                    text += f"🔴 **وضعیت**: منقضی\n"
                    text += f"⚠️ **دسترسی محدود**: فقط کیف پول فعال است\n"
                
                # نمایش دسترسی‌های گروه
                access_data = AccessManager.load_data()
                groups = access_data.get('groups', {})
                if package_group and package_group in groups:
                    group_permissions = groups[package_group]
                    text += f"\n🔐 **مجوزهای شما** ({len(group_permissions)} مورد):\n"
                    for perm in group_permissions:
                        if perm in PERM_DISPLAY:
                            text += f"✅ {PERM_DISPLAY[perm]['label']}\n"
                        else:
                            text += f"✅ {perm}\n"
                else:
                    text += f"\n❌ گروه دسترسی یافت نشد.\n"
                
                if is_active:
                    keyboard = [
                        [InlineKeyboardButton("🔄 تمدید اشتراک", callback_data="renew_subscription")],
                        [InlineKeyboardButton("⬆️ ارتقای پکیج", callback_data="upgrade_my_package")],
                        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")]
                    ]
                else:
                    keyboard = [
                        [InlineKeyboardButton("🔄 تمدید اشتراک", callback_data="renew_subscription")],
                        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")],
                        [InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="contact_support")]
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
            logger.error(f"Error in show_user_subscription_status for user {chat_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش وضعیت اشتراک: {str(e)}"
            )

    @staticmethod
    async def renew_subscription(chat_id, context, message_id=None):
        """
        تمدید اشتراک فعلی کاربر
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            is_active, package, days_left = AdminManager.check_subscription_status(user_id)
            
            if not package:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما هیچ پکیج اشتراکی ندارید. لطفاً ابتدا پکیج تهیه کنید."
                )
                return

            package_name = package.get('name', 'نامشخص')
            price = package.get('price', 0)
            duration = package.get('duration_days', 30)

            text = f"🔄 **تمدید اشتراک**\n\n"
            text += f"📦 **پکیج فعلی**: {package_name}\n"
            text += f"💰 **قیمت تمدید**: {price:,} تومان\n"
            text += f"⏱️ **مدت تمدید**: {duration} روز\n"
            
            if is_active:
                text += f"📅 **روزهای باقی‌مانده**: {days_left} روز\n"
                text += f"⏰ **تاریخ انقضا پس از تمدید**: {(datetime.now() + timedelta(days=duration + days_left)).strftime('%Y/%m/%d')}\n\n"
            else:
                text += f"🔴 **وضعیت**: منقضی\n\n"
            
            text += "آیا می‌خواهید اشتراک خود را تمدید کنید؟"

            keyboard = [
                [InlineKeyboardButton(f"✅ بله، تمدید به قیمت {price:,} تومان", callback_data="confirm_renewal")],
                [InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_renewal")],
                [InlineKeyboardButton("⬆️ ارتقای پکیج", callback_data="upgrade_my_package")],
                [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")]
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
            logger.error(f"Error in renew_subscription for user {chat_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تمدید اشتراک: {str(e)}"
            )

    @staticmethod
    async def confirm_subscription_renewal(chat_id, context, message_id=None):
        """
        تأیید و اجرای تمدید اشتراک
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            is_active, package, days_left = AdminManager.check_subscription_status(user_id)
            
            if not package:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            price = package.get('price', 0)
            duration = package.get('duration_days', 30)
            package_name = package.get('name', 'نامشخص')

            # بررسی موجودی کیف پول
            wallet_balance = await WalletManager.get_balance(user_id)
            
            if wallet_balance < price:
                shortage = price - wallet_balance
                text = f"❌ **موجودی کافی نیست!**\n\n"
                text += f"💰 **قیمت تمدید**: {price:,} تومان\n"
                text += f"💵 **موجودی شما**: {wallet_balance:,} تومان\n"
                text += f"💸 **کمبود**: {shortage:,} تومان\n\n"
                text += "لطفاً کیف پول خود را شارژ کنید."
                
                keyboard = [
                    [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")],
                    [InlineKeyboardButton("بازگشت", callback_data="my_subscription_status")]
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
                return

            # کسر مبلغ از کیف پول
            success = await WalletManager.deduct_balance(user_id, price)
            if not success:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ خطا در کسر مبلغ از کیف پول!"
                )
                return

            # بروزرسانی تاریخ انقضا
            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            
            if str(user_id) in admins:
                admin_data = admins[str(user_id)]
                
                # محاسبه تاریخ انقضا جدید
                current_expiry = admin_data.get('subscription_expiry')
                if current_expiry and is_active:
                    # اگر هنوز فعال است، مدت زمان را اضافه کن
                    current_expiry_date = datetime.fromisoformat(current_expiry)
                    new_expiry_date = current_expiry_date + timedelta(days=duration)
                else:
                    # اگر منقضی شده، از الان شروع کن
                    new_expiry_date = datetime.now() + timedelta(days=duration)
                
                admin_data['subscription_expiry'] = new_expiry_date.isoformat()
                admin_data['subscription_renewed_at'] = datetime.now().isoformat()
                admin_data['subscription_renewed_by'] = user_id
                
                AccessManager.save_data(access_data)

                text = f"✅ **اشتراک با موفقیت تمدید شد!**\n\n"
                text += f"📦 **پکیج**: {package_name}\n"
                text += f"💰 **مبلغ کسر شده**: {price:,} تومان\n"
                text += f"⏰ **تاریخ انقضا جدید**: {new_expiry_date.strftime('%Y/%m/%d %H:%M')}\n"
                text += f"💵 **موجودی باقی‌مانده**: {wallet_balance - price:,} تومان\n\n"
                text += "از تمامی امکانات پکیج خود استفاده کنید!"

                keyboard = [
                    [InlineKeyboardButton("📊 وضعیت اشتراک", callback_data="my_subscription_status")],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
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
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ اطلاعات ادمین یافت نشد!"
                )

        except Exception as e:
            logger.error(f"Error in confirm_subscription_renewal for user {chat_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تأیید تمدید اشتراک: {str(e)}"
            )

    @staticmethod
    async def upgrade_user_package(chat_id, context, message_id=None):
        """
        ارتقای پکیج توسط کاربر
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            is_active, current_package, days_left = AdminManager.check_subscription_status(user_id)
            
            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})

            if not packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ هیچ پکیجی موجود نیست!"
                )
                return

            text = f"⬆️ **ارتقای پکیج اشتراک**\n\n"
            
            if current_package:
                text += f"📦 **پکیج فعلی شما**: {current_package.get('name', 'نامشخص')}\n"
                text += f"💰 **قیمت فعلی**: {current_package.get('price', 0):,} تومان\n\n"
            else:
                text += "📦 **پکیج فعلی**: ندارید\n\n"
            
            text += "پکیج‌های موجود برای ارتقا:\n\n"

            keyboard = []
            for package_id, package in packages.items():
                if not current_package or package_id != current_package.get('id', ''):
                    package_name = package.get('name', package_id)
                    price = package.get('price', 0)
                    duration = package.get('duration_days', 30)
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{package_name} - {price:,} تومان ({duration} روز)", 
                            callback_data=f"user_upgrade:{package_id}"
                        )
                    ])

            if not keyboard:
                text += "❌ هیچ پکیج دیگری برای ارتقا موجود نیست!"
                keyboard = [[InlineKeyboardButton("بازگشت", callback_data="my_subscription_status")]]
            else:
                keyboard.append([
                    InlineKeyboardButton("بازگشت به وضعیت اشتراک", callback_data="my_subscription_status")
                ])

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
            logger.error(f"Error in upgrade_user_package for user {chat_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در ارتقای پکیج: {str(e)}"
            )

    @staticmethod
    async def confirm_user_package_upgrade(chat_id, context, package_id, message_id=None):
        """
        تأیید ارتقای پکیج توسط کاربر
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            
            if package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            new_package = packages[package_id]
            price = new_package.get('price', 0)
            package_name = new_package.get('name', package_id)
            duration = new_package.get('duration_days', 30)

            # بررسی موجودی کیف پول
            wallet_balance = await WalletManager.get_balance(user_id)
            
            if wallet_balance < price:
                shortage = price - wallet_balance
                text = f"❌ **موجودی کافی نیست!**\n\n"
                text += f"💰 **قیمت ارتقا**: {price:,} تومان\n"
                text += f"💵 **موجودی شما**: {wallet_balance:,} تومان\n"
                text += f"💸 **کمبود**: {shortage:,} تومان\n\n"
                text += "لطفاً کیف پول خود را شارژ کنید."
                
                keyboard = [
                    [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")],
                    [InlineKeyboardButton("بازگشت", callback_data="upgrade_my_package")]
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
                return

            text = f"⬆️ **تأیید ارتقای پکیج**\n\n"
            text += f"📦 **پکیج جدید**: {package_name}\n"
            text += f"💰 **قیمت**: {price:,} تومان\n"
            text += f"⏱️ **مدت**: {duration} روز\n"
            text += f"💵 **موجودی فعلی**: {wallet_balance:,} تومان\n"
            text += f"💵 **موجودی پس از ارتقا**: {wallet_balance - price:,} تومان\n\n"
            text += "آیا از ارتقای پکیج اطمینان دارید؟"

            keyboard = [
                [InlineKeyboardButton("✅ بله، ارتقا بده", callback_data=f"execute_upgrade:{package_id}")],
                [InlineKeyboardButton("❌ خیر، انصراف", callback_data="upgrade_my_package")],
                [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_menu")]
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
            logger.error(f"Error in confirm_user_package_upgrade for user {chat_id} and package {package_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تأیید ارتقای پکیج: {str(e)}"
            )

    @staticmethod
    async def execute_user_package_upgrade(chat_id, context, package_id, message_id=None):
        """
        اجرای ارتقای پکیج توسط کاربر
        """
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            access_data = AccessManager.load_data()
            packages = access_data.get('subscription_packages', {})
            admins = access_data.get('admins', {})
            
            if package_id not in packages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ پکیج یافت نشد!"
                )
                return

            if str(user_id) not in admins:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ اطلاعات ادمین یافت نشد!"
                )
                return

            new_package = packages[package_id]
            price = new_package.get('price', 0)
            package_name = new_package.get('name', package_id)
            duration = new_package.get('duration_days', 30)
            admin_data = admins[str(user_id)]

            # کسر مبلغ از کیف پول
            success = await WalletManager.deduct_balance(user_id, price)
            if not success:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ خطا در کسر مبلغ از کیف پول!"
                )
                return

            # بروزرسانی اطلاعات اشتراک
            old_package_id = admin_data.get('subscription_package')
            new_expiry_date = datetime.now() + timedelta(days=duration)
            
            admin_data['subscription_package'] = package_id
            admin_data['subscription_expiry'] = new_expiry_date.isoformat()
            admin_data['subscription_upgraded_at'] = datetime.now().isoformat()
            admin_data['subscription_upgraded_by'] = user_id
            admin_data['previous_package'] = old_package_id
            # دسترسی‌ها اکنون از گروه پکیج گرفته می‌شود
            # admin_data['permissions'] = new_package.get('permissions', [])

            AccessManager.save_data(access_data)

            AccessManager.save_data(access_data)

            # دریافت موجودی جدید
            new_balance = await WalletManager.get_balance(user_id)

            text = f"✅ **پکیج با موفقیت ارتقا یافت!**\n\n"
            text += f"📦 **پکیج جدید**: {package_name}\n"
            text += f"💰 **مبلغ کسر شده**: {price:,} تومان\n"
            text += f"⏰ **تاریخ انقضا**: {new_expiry_date.strftime('%Y/%m/%d %H:%M')}\n"
            text += f"💵 **موجودی باقی‌مانده**: {new_balance:,} تومان\n"
            text += f"🔐 **مجوزهای جدید**: {len(new_package.get('permissions', []))} مورد\n\n"
            text += "از امکانات جدید پکیج خود لذت ببرید!"

            keyboard = [
                [InlineKeyboardButton("📊 وضعیت اشتراک", callback_data="my_subscription_status")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
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
            logger.error(f"Error in execute_user_package_upgrade for user {chat_id} and package {package_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در اجرای ارتقای پکیج: {str(e)}"
            )

    @staticmethod
    async def process_subscription_renewal(chat_id, context, admin_id, renewal_type):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز تمدید اشتراک را ندارید!"
                )
                return

            access_data = AccessManager.load_data()
            admins = access_data.get('admins', {})
            admin_data = admins.get(str(admin_id), {})
            
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}
            
            subscription_price = admin_data.get('subscription_price', 0)
            if subscription_price <= 0:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ قیمت اشتراک تنظیم نشده است. ابتدا قیمت را تنظیم کنید."
                )
                return

            # محاسبه مبلغ بر اساس نوع تمدید
            if renewal_type == 'monthly':
                amount = subscription_price
                days = 30
            elif renewal_type == 'yearly':
                amount = subscription_price * 12
                days = 365
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ نوع تمدید نامعتبر."
                )
                return

            wallets = ReceiptManager.load_wallets()
            wallet_balance = wallets.get(str(admin_id), 0)
            
            if wallet_balance < amount:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ موجودی کیف پول کافی نیست.\n💰 موجودی: {wallet_balance:,} تومان\n💸 مبلغ مورد نیاز: {amount:,} تومان",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data=f"charge_admin_wallet:{admin_id}")],
                        [InlineKeyboardButton("بازگشت", callback_data=f"view_subscription:{admin_id}")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            # تمدید اشتراک
            from datetime import datetime, timedelta
            current_expiry = admin_data.get('subscription_expiry')
            if current_expiry:
                try:
                    expiry = datetime.fromisoformat(current_expiry)
                    if expiry < datetime.now():
                        # اگر منقضی شده، از امروز شروع کن
                        expiry = datetime.now()
                except ValueError:
                    expiry = datetime.now()
            else:
                expiry = datetime.now()
            
            new_expiry = expiry + timedelta(days=days)
            admin_data['subscription_expiry'] = new_expiry.isoformat()
            
            # کسر از کیف پول
            wallets[str(admin_id)] = wallet_balance - amount
            
            # ذخیره تغییرات
            admins[str(admin_id)] = admin_data
            access_data['admins'] = admins
            AccessManager.save_data(access_data)
            ReceiptManager.save_wallets(wallets)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ اشتراک ادمین {admin_id} با موفقیت تمدید شد!\n\n💰 مبلغ کسر شده: {amount:,} تومان\n📅 تاریخ جدید انقضا: {new_expiry.strftime('%Y-%m-%d')}\n💵 موجودی جدید: {(wallet_balance - amount):,} تومان",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به پروفایل اشتراک", callback_data=f"view_subscription:{admin_id}")]]),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in process_subscription_renewal for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در تمدید اشتراک: {str(e)}"
            )

    @staticmethod
    async def show_subscription_renewal(chat_id, context, admin_id, message_id=None):
        """Show subscription renewal options for admin"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins') and str(user_id) != str(admin_id):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز تمدید اشتراک را ندارید!"
                )
                return

            # Get current wallet balance
            wallets = ReceiptManager.load_wallets()
            wallet_balance = wallets.get(str(admin_id), 0)

            # Subscription prices (in Toman)
            monthly_price = 500000  # 500,000 Toman per month
            yearly_price = 5000000  # 5,000,000 Toman per year (10% discount)

            text = f"🔄 **تمدید اشتراک ربات**\n\n**موجودی کیف پول**: {wallet_balance:,} تومان\n\n**طرح‌های اشتراک**:\n"
            text += f"📅 **ماهانه**: {monthly_price:,} تومان (30 روز)\n"
            text += f"📅 **سالانه**: {yearly_price:,} تومان (365 روز) - 10% تخفیف\n\n"

            keyboard = []
            if wallet_balance >= monthly_price:
                keyboard.append([InlineKeyboardButton(f"📅 تمدید ماهانه ({monthly_price:,} تومان)", callback_data=f"renew_monthly:{admin_id}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ موجودی کافی نیست - ماهانه ({monthly_price:,} تومان)", callback_data="insufficient_balance")])

            if wallet_balance >= yearly_price:
                keyboard.append([InlineKeyboardButton(f"📅 تمدید سالانه ({yearly_price:,} تومان)", callback_data=f"renew_yearly:{admin_id}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ موجودی کافی نیست - سالانه ({yearly_price:,} تومان)", callback_data="insufficient_balance")])

            keyboard.append([InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge")])
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data=f"view_admin:{admin_id}")])

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
            logger.error(f"Error in show_subscription_renewal for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش منوی تمدید اشتراک: {str(e)}"
            )

    @staticmethod
    async def process_subscription_renewal(chat_id, context, admin_id, renewal_type):
        """Process subscription renewal payment"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'manage_admins') and str(user_id) != str(admin_id):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز تمدید اشتراک را ندارید!"
                )
                return

            # Get renewal prices
            monthly_price = 500000
            yearly_price = 5000000

            if renewal_type == "monthly":
                price = monthly_price
                days = 30
            elif renewal_type == "yearly":
                price = yearly_price
                days = 365
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ نوع تمدید نامعتبر!"
                )
                return

            # Check wallet balance
            wallets = ReceiptManager.load_wallets()
            wallet_balance = wallets.get(str(admin_id), 0)

            if wallet_balance < price:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ موجودی کیف پول کافی نیست!\n\nموجودی: {wallet_balance:,} تومان\nمورد نیاز: {price:,} تومان"
                )
                return

            # Calculate new expiry date
            from datetime import datetime, timedelta
            access_data = AccessManager.load_data()
            admin_data = access_data.get('admins', {}).get(str(admin_id), {})
            if isinstance(admin_data, str):
                admin_data = {'group': admin_data}

            current_expiry = admin_data.get('license_expiry')
            if current_expiry:
                try:
                    base_date = datetime.fromisoformat(current_expiry)
                    # If current expiry is in future, extend from there; otherwise from today
                    if base_date > datetime.now():
                        new_expiry = base_date + timedelta(days=days)
                    else:
                        new_expiry = datetime.now() + timedelta(days=days)
                except ValueError:
                    new_expiry = datetime.now() + timedelta(days=days)
            else:
                new_expiry = datetime.now() + timedelta(days=days)

            # Update admin data
            admin_data['license_expiry'] = new_expiry.date().isoformat()
            access_data['admins'][str(admin_id)] = admin_data
            AccessManager.save_data(access_data)

            # Deduct from wallet
            wallets[str(admin_id)] = wallet_balance - price
            ReceiptManager.save_wallets(wallets)

            # Send confirmation
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **اشتراک با موفقیت تمدید شد!**\n\nنوع تمدید: {'ماهانه' if renewal_type == 'monthly' else 'سالانه'}\nمدت زمان: {days} روز\nتاریخ انقضا جدید: {new_expiry.date()}\nمبلغ کسر شده: {price:,} تومان\nموجودی جدید: {wallets[str(admin_id)]:,} تومان",
                parse_mode="Markdown"
            )

            # If renewing own subscription, show main menu
            if str(user_id) == str(admin_id):
                from hotel_bot.menu_manager import MenuManager
                await MenuManager.show_main_menu(user_id, context)

        except Exception as e:
            logger.error(f"Error in process_subscription_renewal for admin_id {admin_id}: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در پردازش تمدید اشتراک: {str(e)}"
            )
            from hotel_bot.menu_manager import MenuManager
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
                from hotel_bot.menu_manager import MenuManager
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
            from hotel_bot.menu_manager import MenuManager
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
                from hotel_bot.menu_manager import MenuManager
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
            from hotel_bot.menu_manager import MenuManager
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
                from hotel_bot.menu_manager import MenuManager
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
            from hotel_bot.menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)