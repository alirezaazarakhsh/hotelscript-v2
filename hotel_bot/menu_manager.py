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

**امکانات ورژن 1.2 ربات:**

📦 **بکاپ‌گیری دستی** از دیتابیس و پوشه مدیا
📋 **لیست رزروها** با امکان تایید یا رد و جستجو پیشرفته
📮 **پشتیبانی** ارتباط سریع با ادمین
📋 **راهنمای بکاپ‌گیری** (در حال توسعه...)
💰 **شارژ کیف پول** برای دسترسی به خدمات بیشتر
💸 **مشاهده موجودی کیف پول** برای بررسی وضعیت مالی
💰 **مدیریت کیف پول کاربران** با قابلیت جستجو و شارژ/برداشت
💎 **مدیریت امتیازات باشگاه مشتریان** با امکان افزودن/کاهش امتیازات
⚙️ **کنترل پنل مدیریتی** برای مدیریت ادمین‌ها و دسترسی‌ها
"""
            keyboard = []
            buttons = []
            if AccessManager.is_allowed(user_id, 'wallet_charge'):
                buttons.append(InlineKeyboardButton("💰 شارژ کیف پول بات", callback_data="wallet_charge"))
            if AccessManager.is_allowed(user_id, 'view_reservations'):
                buttons.append(InlineKeyboardButton("📋 لیست رزروها", callback_data="view_reservations"))
            if AccessManager.is_allowed(user_id, 'support'):
                buttons.append(InlineKeyboardButton("📮 پشتیبانی", callback_data="support"))
            if AccessManager.is_allowed(user_id, 'backup_db') or AccessManager.is_allowed(user_id, 'backup_media'):
                buttons.append(InlineKeyboardButton("📦 بکاپ‌گیری", callback_data="backup_menu"))
            if AccessManager.is_allowed(user_id, 'manage_wallet'):
                buttons.append(InlineKeyboardButton("💰 مدیریت کیف پول کاربران سایت", callback_data="manage_wallet"))
            if AccessManager.is_allowed(user_id, 'manage_points'):
                buttons.append(InlineKeyboardButton("💎 مدیریت امتیازات باشگاه مشتریان", callback_data="manage_points"))
            
            # Arrange buttons in rows of 2
            for i in range(0, len(buttons), 2):
                keyboard.append(buttons[i:i+2])
            
            # Add control panel separately at the bottom
            if AccessManager.is_allowed(user_id, 'manage_admins'):
                keyboard.append([InlineKeyboardButton("⚙️ کنترل پنل", callback_data="control_panel")])
        
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
            if AccessManager.is_allowed(user_id, 'backup_info'):
                keyboard.append([InlineKeyboardButton("📋 نحوه بکاپ‌گیری", callback_data="backup_info")])
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
    async def show_manage_wallet_menu(query, user_id, context, page=1, search_query=None):
        try:
            from authentication.models import BaseUser
            from finance.models import Wallet
            from asgiref.sync import sync_to_async
            from django.db.models import Q
            
            per_page = 5
            offset = (page - 1) * per_page
            
            # Get total users count with search filter
            @sync_to_async
            def get_total_users(search_query):
                if search_query:
                    return BaseUser.objects.filter(
                        Q(phone_number__icontains=search_query) |
                        Q(natural_profile__first_name__icontains=search_query) |
                        Q(natural_profile__last_name__icontains=search_query) |
                        Q(admin__first_name__icontains=search_query) |
                        Q(admin__last_name__icontains=search_query)
                    ).count()
                return BaseUser.objects.count()
            
            total_users = await get_total_users(search_query)
            total_pages = (total_users + per_page - 1) // per_page
            
            # Get users for this page with search filter
            @sync_to_async
            def get_users(offset, per_page, search_query):
                users = []
                queryset = BaseUser.objects.all()
                
                if search_query:
                    queryset = queryset.filter(
                        Q(phone_number__icontains=search_query) |
                        Q(natural_profile__first_name__icontains=search_query) |
                        Q(natural_profile__last_name__icontains=search_query) |
                        Q(admin__first_name__icontains=search_query) |
                        Q(admin__last_name__icontains=search_query)
                    )
                
                for user in queryset[offset:offset + per_page]:
                    name = ""
                    if hasattr(user, 'natural_profile') and user.natural_profile:
                        name = f"{user.natural_profile.first_name or ''} {user.natural_profile.last_name or ''}".strip()
                    elif hasattr(user, 'admin') and user.admin:
                        name = f"{user.admin.first_name or ''} {user.admin.last_name or ''}".strip()
                    if not name:
                        name = user.phone_number
                    users.append({
                        'id': user.id,
                        'phone': user.phone_number,
                        'name': name
                    })
                return users
            
            users = await get_users(offset, per_page, search_query)
            
            search_text = f"\n🔍 نتایج جستجو برای: '{search_query}'" if search_query else ""
            text = f"💰 **مدیریت کیف پول کاربران سایت** (صفحه {page} از {total_pages}){search_text}\n\nلیست کاربران سایت. روی نام کاربر کلیک کنید تا کیف پولش را مدیریت کنید.\n\n"
            keyboard = []
            
            # Add search button if not searching
            if not search_query:
                keyboard.append([InlineKeyboardButton("🔍 جستجو", callback_data="search_wallet_users")])
            
            for i, user in enumerate(users, start=(page-1)*per_page + 1):
                keyboard.append([InlineKeyboardButton(f"{i}. {user['name']} - {user['phone']}", callback_data=f"manage_user_wallet:{user['id']}")])
            
            # Pagination buttons
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton(f"⬅️ صفحه {page-1}", callback_data=f"wallet_page:{page-1}:{search_query or ''}"))
            if page < total_pages:
                pagination_buttons.append(InlineKeyboardButton(f"صفحه {page+1} ➡️", callback_data=f"wallet_page:{page+1}:{search_query or ''}"))
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)
            
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="manage_points")])
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
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی مدیریت کیف پول: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id if query.message else None, query.message.chat_id if query.message else user_id)

    @staticmethod
    async def search_wallet_users(user_id, context):
        """Start wallet users search"""
        try:
            text = "🔍 **جستجوی کاربران کیف پول**\n\nلطفاً نام کاربر یا شماره تلفن را وارد کنید:\n\n📝 مثال: 09123456789 یا ساشا"
            keyboard = [[InlineKeyboardButton("لغو جستجو", callback_data="manage_wallet")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            # Set state for waiting for search input
            context.user_data['state'] = 'waiting_for_wallet_search'
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در شروع جستجو: {str(e)}")

    @staticmethod
    async def process_wallet_search(user_id, context, search_query):
        """Process wallet users search query"""
        try:
            if not search_query or search_query.strip() == "":
                await context.bot.send_message(chat_id=user_id, text="❌ لطفاً یک عبارت جستجو وارد کنید.")
                return
            
            search_query = search_query.strip()
            
            # Create a mock query object for the search
            class MockQuery:
                def __init__(self):
                    self.message = None
            
            mock_query = MockQuery()
            # Search wallet users
            await MenuManager.show_manage_wallet_menu(mock_query, user_id, context, page=1, search_query=search_query)
            
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در جستجوی کاربران کیف پول: {str(e)}")

    @staticmethod
    async def show_points_main_menu(query, user_id, context):
        """Show main points management menu"""
        try:
            text = "💎 **مدیریت امتیازات باشگاه مشتریان**\n\nاز این بخش می‌توانید امتیازات کاربران باشگاه مشتریان را مدیریت کنید.\n\n**امکانات موجود**:\n• مشاهده لیست کاربران و امتیازات آن‌ها\n• افزودن یا کسر امتیازات کاربران\n• مدیریت امتیازات باشگاه مشتریان"
            keyboard = [
                [InlineKeyboardButton("📋 مشاهده لیست کاربران و امتیازات", callback_data="view_points_users")],
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
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی مدیریت امتیازات: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id if query.message else None, query.message.chat_id if query.message else user_id)

    @staticmethod
    async def show_manage_points_menu(query, user_id, context, page=1):
        try:
            from bashgah_moshtarian.models import CustomerClubPoint
            from asgiref.sync import sync_to_async
            
            per_page = 5
            offset = (page - 1) * per_page
            
            # Get total users count
            @sync_to_async
            def get_total_users():
                return CustomerClubPoint.objects.count()
            
            total_users = await get_total_users()
            total_pages = (total_users + per_page - 1) // per_page
            
            # Get users for this page
            @sync_to_async
            def get_users(offset, per_page):
                users = []
                for point in CustomerClubPoint.objects.select_related('user').all()[offset:offset + per_page]:
                    name = ""
                    if hasattr(point.user, 'natural_profile') and point.user.natural_profile:
                        name = f"{point.user.natural_profile.first_name or ''} {point.user.natural_profile.last_name or ''}".strip()
                    elif hasattr(point.user, 'admin') and point.user.admin:
                        name = f"{point.user.admin.first_name or ''} {point.user.admin.last_name or ''}".strip()
                    if not name:
                        name = point.user.phone_number
                    users.append({
                        'id': point.user.id,
                        'phone': point.user.phone_number,
                        'name': name,
                        'points': point.points
                    })
                return users
            
            users = await get_users(offset, per_page)
            
            text = f"💎 **مدیریت امتیازات باشگاه مشتریان** (صفحه {page} از {total_pages})\n\nلیست کاربران و امتیازات آن‌ها. روی نام کاربر کلیک کنید تا امتیازاتش را مدیریت کنید.\n\n"
            keyboard = []
            
            for user in users:
                keyboard.append([InlineKeyboardButton(f"{user['name']} ({user['phone']}) - {user['points']:,} امتیاز", callback_data=f"manage_user_points:{user['id']}")])
            
            # Pagination buttons
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton(f"⬅️ صفحه {page-1}", callback_data=f"points_page:{page-1}"))
            if page < total_pages:
                pagination_buttons.append(InlineKeyboardButton(f"صفحه {page+1} ➡️", callback_data=f"points_page:{page+1}"))
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)
            
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="manage_points")])
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
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش منوی مدیریت امتیازات: {str(e)}")
            await MenuManager.show_main_menu(user_id, context, query.message.message_id if query.message else None, query.message.chat_id if query.message else user_id)