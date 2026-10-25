from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import SUPER_ADMINS
from hotel_bot.access_manager import AccessManager
import logging
from asgiref.sync import sync_to_async
import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zarvantrip.settings')
django.setup()

from authentication.models import Admin, BaseUser
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DjangoAdminManager:
    """مدیریت ادمین‌های وبسایت Django از طریق ربات"""
    
    @staticmethod
    async def show_django_admins_menu(chat_id, context, message_id=None):
        """نمایش منوی مدیریت ادمین‌های وبسایت"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            # بررسی دسترسی
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مدیریت ادمین‌های سایت را ندارید!"
                )
                return
            
            # دریافت لیست ادمین‌های Django
            admins = await sync_to_async(lambda: list(Admin.objects.select_related('base_user').all()))()
            
            text = "👥 **مدیریت ادمین‌های وبسایت Django**\n\n"
            text += f"📊 تعداد کل ادمین‌ها: {len(admins)}\n\n"
            
            if not admins:
                text += "❌ هیچ ادمینی در سیستم وجود ندارد"
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="control_panel")]]
            else:
                text += "📋 **لیست ادمین‌ها:**\n\n"
                keyboard = []
                for admin in admins[:15]:
                    phone = admin.base_user.phone_number
                    name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
                    status = "✅ " if admin.base_user.is_active else "❌ "
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{status}{name} ({phone})",
                            callback_data=f"django_admin_detail:{admin.base_user.id}"
                        )
                    ])
                keyboard.append([InlineKeyboardButton("📱 مدیریت توکن‌های OTP", callback_data="otp_menu")])
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="control_panel")])
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
            logger.error(f"Error in show_django_admins_menu: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def show_django_admin_detail(chat_id, context, base_user_id, message_id=None):
        """نمایش جزئیات یک ادمین Django"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = await sync_to_async(BaseUser.objects.get)(id=base_user_id)
            admin = await sync_to_async(Admin.objects.get)(base_user=base_user)
            
            phone = base_user.phone_number
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            # اطلاعات پایه
            text = f"👤 **جزئیات ادمین وبسایت**\n\n"
            text += f"**نام:** {name}\n"
            text += f"**شماره تماس:** {phone}\n"
            text += f"**ID کاربر:** {base_user.id}\n\n"
            
            # وضعیت‌ها
            text += "**وضعیت‌ها:**\n"
            text += f"🔹 فعال: {'✅' if base_user.is_active else '❌'}\n"
            text += f"🔹 Staff: {'✅' if base_user.is_staff else '❌'}\n"
            text += f"🔹 Superuser: {'✅' if base_user.is_superuser else '❌'}\n\n"
            
            # گروه‌ها
            groups = base_user.groups.all()
            text += f"**گروه‌های Django:** ({groups.count()})\n"
            if groups.exists():
                for group in groups:
                    text += f"• {group.name}\n"
            else:
                text += "هیچ گروهی تعیین نشده\n"
            
            text += "\n"
            
            # مجوزهای مستقیم
            user_permissions = base_user.user_permissions.all()
            text += f"**مجوزهای مستقیم:** ({user_permissions.count()})\n"
            if user_permissions.exists():
                for perm in user_permissions[:5]:  # نمایش 5 مورد اول
                    text += f"• {perm.name}\n"
                if user_permissions.count() > 5:
                    text += f"... و {user_permissions.count() - 5} مجوز دیگر\n"
            else:
                text += "بدون مجوز مستقیم\n"
            
            keyboard = [
                [InlineKeyboardButton("📱 مدیریت OTP", callback_data=f"otp_admin:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="django_admins_menu")]
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
            logger.error(f"Error in show_django_admin_detail: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def manage_admin_groups(chat_id, context, base_user_id, message_id=None):
        """مدیریت گروه‌های یک ادمین"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            current_groups = set(base_user.groups.values_list('id', flat=True))
            all_groups = Group.objects.all()
            
            text = f"👥 **مدیریت گروه‌های Django**\n\n"
            text += f"**ادمین:** {name}\n\n"
            text += "**گروه‌های موجود:**\n\n"
            
            keyboard = []
            for group in all_groups:
                is_member = group.id in current_groups
                status = "✅" if is_member else "⚪"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status} {group.name}",
                        callback_data=f"toggle_group:{base_user_id}:{group.id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"django_admin_detail:{base_user_id}")])
            
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
            logger.error(f"Error in manage_admin_groups: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def toggle_admin_group(chat_id, context, base_user_id, group_id, message_id=None):
        """افزودن/حذف ادمین از یک گروه"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            group = Group.objects.get(id=group_id)
            
            if base_user.groups.filter(id=group_id).exists():
                base_user.groups.remove(group)
                action = "حذف شد از"
            else:
                base_user.groups.add(group)
                action = "اضافه شد به"
            
            # بازگشت به منوی مدیریت گروه‌ها
            await DjangoAdminManager.manage_admin_groups(chat_id, context, base_user_id, message_id)
            
            # ارسال پیام موفقیت
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ گروه '{group.name}' {action} ادمین"
            )
        
        except Exception as e:
            logger.error(f"Error in toggle_admin_group: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def toggle_admin_status(chat_id, context, base_user_id, message_id=None):
        """فعال/غیرفعال کردن ادمین"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            # تغییر وضعیت
            base_user.is_active = not base_user.is_active
            base_user.save()
            
            status = "فعال" if base_user.is_active else "غیرفعال"
            
            # بازگشت به جزئیات ادمین
            await DjangoAdminManager.show_django_admin_detail(chat_id, context, base_user_id, message_id)
            
            # ارسال پیام موفقیت
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ ادمین '{name}' {status} شد"
            )
        
        except Exception as e:
            logger.error(f"Error in toggle_admin_status: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def show_django_groups_menu(chat_id, context, message_id=None):
        """نمایش منوی مدیریت گروه‌های Django"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            groups = Group.objects.all()
            
            text = "👥 **گروه‌های Django**\n\n"
            text += f"📊 تعداد کل گروه‌ها: {groups.count()}\n\n"
            
            keyboard = []
            for group in groups:
                perm_count = group.permissions.count()
                user_count = group.user_set.count()
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{group.name} ({user_count} کاربر, {perm_count} مجوز)",
                        callback_data=f"django_group_detail:{group.id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ ایجاد گروه جدید", callback_data="create_django_group")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="django_admins_menu")])
            
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
            logger.error(f"Error in show_django_groups_menu: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def show_django_group_detail(chat_id, context, group_id, message_id=None):
        """نمایش جزئیات یک گروه Django"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            group = Group.objects.get(id=group_id)
            permissions = group.permissions.all()
            users = group.user_set.all()
            
            text = f"👥 **جزئیات گروه: {group.name}**\n\n"
            text += f"**تعداد کاربران:** {users.count()}\n"
            text += f"**تعداد مجوزها:** {permissions.count()}\n\n"
            
            if users.exists():
                text += "**کاربران:**\n"
                for user in users[:10]:
                    try:
                        admin = Admin.objects.get(base_user=user)
                        name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or user.phone_number
                    except:
                        name = user.phone_number
                    text += f"• {name}\n"
                if users.count() > 10:
                    text += f"... و {users.count() - 10} کاربر دیگر\n"
            
            keyboard = [
                [InlineKeyboardButton("🔐 مدیریت مجوزها", callback_data=f"manage_group_perms:{group_id}")],
                [InlineKeyboardButton("👥 مدیریت اعضا", callback_data=f"manage_group_users:{group_id}")],
                [InlineKeyboardButton("✏️ تغییر نام", callback_data=f"rename_group:{group_id}")],
                [InlineKeyboardButton("🗑️ حذف گروه", callback_data=f"delete_django_group:{group_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="django_groups_menu")]
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
            logger.error(f"Error in show_django_group_detail: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def manage_django_admin_permissions(chat_id, context, base_user_id, message_id=None):
        """مدیریت مجوزهای مستقیم یک ادمین"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            text = f"🔐 **مدیریت مجوزهای {name}**\n\n"
            text += "⚠️ **توجه:** این بخش برای مجوزهای پیشرفته است.\n"
            text += "توصیه می‌شود از گروه‌ها استفاده کنید.\n\n"
            
            user_perms = base_user.user_permissions.all()
            text += f"**مجوزهای فعلی:** {user_perms.count()}\n\n"
            
            if user_perms.exists():
                for perm in user_perms[:10]:
                    text += f"• {perm.name}\n"
                if user_perms.count() > 10:
                    text += f"... و {user_perms.count() - 10} مجوز دیگر\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ افزودن مجوز", callback_data=f"add_admin_perm:{base_user_id}")],
                [InlineKeyboardButton("➖ حذف مجوز", callback_data=f"remove_admin_perm:{base_user_id}")],
                [InlineKeyboardButton("🔄 ریست کردن مجوزها", callback_data=f"reset_admin_perms:{base_user_id}")],
                [InlineKeyboardButton("⭐ تبدیل به Staff", callback_data=f"make_staff:{base_user_id}")],
                [InlineKeyboardButton("👑 تبدیل به Superuser", callback_data=f"make_superuser:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"django_admin_detail:{base_user_id}")]
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
            logger.error(f"Error in manage_django_admin_permissions: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def make_staff(chat_id, context, base_user_id, message_id=None):
        """تبدیل ادمین به Staff"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            base_user.is_staff = not base_user.is_staff
            base_user.save()
            
            status = "Staff" if base_user.is_staff else "Non-Staff"
            
            await DjangoAdminManager.show_django_admin_detail(chat_id, context, base_user_id, message_id)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ ادمین به {status} تبدیل شد")
        
        except Exception as e:
            logger.error(f"Error in make_staff: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def make_superuser(chat_id, context, base_user_id, message_id=None):
        """تبدیل ادمین به Superuser"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            # فقط سوپرادمین‌های ربات می‌توانند این کار را انجام دهند
            if user_id not in SUPER_ADMINS:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ فقط سوپرادمین‌های ربات می‌توانند Superuser تعیین کنند!"
                )
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            base_user.is_superuser = not base_user.is_superuser
            base_user.save()
            
            status = "Superuser" if base_user.is_superuser else "Non-Superuser"
            
            await DjangoAdminManager.show_django_admin_detail(chat_id, context, base_user_id, message_id)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ ادمین به {status} تبدیل شد")
        
        except Exception as e:
            logger.error(f"Error in make_superuser: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
