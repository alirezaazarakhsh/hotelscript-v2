from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import MAX_BACKUPS, PERM_DISPLAY, SUPER_ADMINS
from hotel_bot.access_manager import AccessManager

class MenuManager:
    @staticmethod
    async def show_main_menu(user_id, context, message_id=None, chat_id=None):
        try:
            username = (await context.bot.get_chat_member(user_id=user_id, chat_id=user_id)).user.first_name
            text = f"""
سلام {username}!
به ربات اسکریپت هتل خوش اومدی 👋🏻

در این نسخه از ربات تلاش کرده‌ایم تمامی نیازهای شما را پوشش دهیم و مدیریت اسکریپت را آسان کنیم.

**امکانات ورژن 1.1 ربات:**

📦 **بکاپ‌گیری دستی** از دیتابیس و پوشه مدیا
📋 **لیست رزروها** با امکان تایید یا رد
📮 **پشتیبانی** ارتباط سریع با ادمین
📋 **راهنمای بکاپ‌گیری** (در حال توسعه...)
💰 **شارژ کیف پول** برای دسترسی به خدمات بیشتر
💸 **مشاهده موجودی کیف پول** برای بررسی وضعیت مالی
"""
            keyboard = []
            row = []
            if AccessManager.is_allowed(user_id, 'backup_db') or AccessManager.is_allowed(user_id, 'backup_media'):
                row.append(InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"))
            if AccessManager.is_allowed(user_id, 'view_reservations'):
                row.append(InlineKeyboardButton("📋 لیست رزروها", callback_data="view_reservations"))
            if row:
                keyboard.append(row)
            row = []
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
            if AccessManager.is_allowed(user_id, 'wallet_charge'):
                row.append(InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge"))
            if AccessManager.is_allowed(user_id, 'view_balance'):
                row.append(InlineKeyboardButton("💸 مشاهده موجودی", callback_data="view_balance"))
            if AccessManager.is_allowed(user_id, 'manage_wallet'):
                row.append(InlineKeyboardButton("💰 مدیریت کیف پول", callback_data="manage_wallet"))
            if row:
                keyboard.append(row)
        
            reply_markup = InlineKeyboardMarkup(keyboard)
        
            if message_id and chat_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی اصلی: {str(e)}")

    @staticmethod
    async def show_backup_menu(query, user_id, context):
        try:
            text = "📦 **انتخاب نوع بکاپ‌گیری**\n\nلازم به ذکر است که می‌توانید از دیتابیس یا فولدرهای مدیا بکاپ بگیرید.\n\n**توضیح**: بکاپ دیتابیس داده‌های سایت را حفظ می‌کند، بکاپ مدیا فایل‌های آپلود شده را."
            keyboard = [[
                InlineKeyboardButton("دیتابیس", callback_data="backup_db") if AccessManager.is_allowed(user_id, 'backup_db') else None,
                InlineKeyboardButton("فولدر مدیا", callback_data="backup_media") if AccessManager.is_allowed(user_id, 'backup_media') else None
            ]]
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
            keyboard = [row for row in keyboard if any(row)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش منوی بکاپ‌گیری: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id, query.message.chat_id)

    @staticmethod
    async def show_backup_info(query, user_id, context):
        try:
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
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش اطلاعات بکاپ: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id, query.message.chat_id)

    @staticmethod
    async def show_support_menu(query, user_id, context):
        try:
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
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش منوی پشتیبانی: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id, query.message.chat_id)

    @staticmethod
    async def show_restore_menu(query, user_id, context):
        try:
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
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش منوی ریستور: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id, query.message.chat_id)

    @staticmethod
    async def show_control_panel(query, user_id, context):
        try:
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
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش کنترل پنل: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id, query.message.chat_id)


    @staticmethod
    async def show_profile_edit_menu(query, user_id, context):
            try:
                access_data = AccessManager.load_data()
                profile = access_data.get('profiles', {}).get(str(user_id), {})
                
                text = f"👤 **ویرایش پروفایل شما (ID: {user_id})**\n\nمشخصات فعلی:\n"
                name = profile.get('name') if profile.get('name') is not None else 'ندارد'
                lastname = profile.get('lastname') if profile.get('lastname') is not None else 'ندارد'
                national_id = profile.get('national_id') if profile.get('national_id') is not None else 'ندارد'
                phone = profile.get('phone') if profile.get('phone') is not None else 'ندارد'
                landline = profile.get('landline') if profile.get('landline') is not None else 'ندارد'
                company_name = profile.get('company_name') if profile.get('company_name') is not None else 'ندارد'
                company_reg = profile.get('company_reg') if profile.get('company_reg') is not None else 'ندارد'

                text += f"- نام: {name} \n"
                text += f"- نام خانوادگی: {lastname} \n"
                text += f"- کد ملی: {national_id} \n"
                text += f"- شماره همراه: {phone} \n"
                text += f"- شماره تلفن ثابت: {landline} \n"
                text += f"- نام شرکت: {company_name} \n"
                text += f"- کد ثبت شرکت: {company_reg} \n\n"
                text += "لطفاً بخشی که می‌خواهید ویرایش کنید را انتخاب کنید. اگر تغییری نمی‌خواهید، می‌توانید همان مقدار فعلی را نگه دارید."

                keyboard = [
                    [InlineKeyboardButton("نام", callback_data=f"edit_profile_field:name:{user_id}")],
                    [InlineKeyboardButton("نام خانوادگی", callback_data=f"edit_profile_field:lastname:{user_id}")],
                    [InlineKeyboardButton("کد ملی", callback_data=f"edit_profile_field:national_id:{user_id}")],
                    [InlineKeyboardButton("شماره همراه", callback_data=f"edit_profile_field:phone:{user_id}")],
                    [InlineKeyboardButton("شماره تلفن ثابت", callback_data=f"edit_profile_field:landline:{user_id}")],
                    [InlineKeyboardButton("نام شرکت", callback_data=f"edit_profile_field:company_name:{user_id}")],
                    [InlineKeyboardButton("کد ثبت شرکت", callback_data=f"edit_profile_field:company_reg:{user_id}")],
                    [InlineKeyboardButton("بازگشت", callback_data="go_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                try:
                    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
                except Exception as e:
                    # If editing fails, send a new message
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی ویرایش پروفایل: {str(e)}")
                await MenuManager.show_main_menu(user_id, context, query.message.message_id if query.message else None, query.message.chat_id if query.message else user_id)

    @staticmethod
    async def show_manage_wallet_menu(query, user_id, context):
        try:
            text = "💰 **مدیریت کیف پول کاربران**\n\nشماره موبایل کاربر را وارد کنید تا کیف پولش را مدیریت کنید."
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="go_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            context.user_data['state'] = 'waiting_for_wallet_phone'
            
            try:
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
            except Exception as e:
                # If editing fails, send a new message
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی مدیریت کیف پول: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id if query.message else None, query.message.chat_id if query.message else user_id)