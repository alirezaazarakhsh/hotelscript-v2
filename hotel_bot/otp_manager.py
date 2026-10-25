from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import SUPER_ADMINS
from hotel_bot.access_manager import AccessManager
import logging
import django
import os
import sys
import random
import string

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zarvantrip.settings')
django.setup()

from authentication.models import Admin, BaseUser
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OTPManager:
    """مدیریت توکن‌های OTP و Static برای ادمین‌ها از طریق ربات"""
    
    @staticmethod
    async def show_admin_otp_menu(chat_id, context, message_id=None):
        """نمایش منوی مدیریت OTP ادمین‌های سایت"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            # بررسی دسترسی
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مدیریت OTP را ندارید!"
                )
                return
            
            # دریافت لیست ادمین‌های سایت
            admins = Admin.objects.all()
            
            if not admins.exists():
                text = "📱 **مدیریت توکن‌های OTP**\n\n❌ هیچ ادمینی وجود ندارد"
                keyboard = [
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_admins")]
                ]
            else:
                text = "📱 **مدیریت توکن‌های OTP ادمین‌های سایت**\n\n"
                text += f"تعداد ادمین‌ها: {admins.count()}\n\n"
                text += "📋 **انتخاب ادمین برای مدیریت OTP:**\n\n"
                
                keyboard = []
                for admin in admins[:10]:  # نمایش حداکثر 10 ادمین
                    phone = admin.base_user.phone_number
                    name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
                    
                    # بررسی وجود TOTP و Static Tokens
                    totp_exists = TOTPDevice.objects.filter(user=admin.base_user, confirmed=True).exists()
                    static_exists = StaticDevice.objects.filter(user=admin.base_user, confirmed=True).exists()
                    
                    status = ""
                    if totp_exists:
                        status += "🔐 "
                    if static_exists:
                        status += "📱 "
                    if not status:
                        status = "⚪ "
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{status}{name} ({phone})",
                            callback_data=f"otp_admin:{admin.base_user.id}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="manage_admins")])
            
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
            logger.error(f"Error in show_admin_otp_menu: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def show_admin_otp_options(chat_id, context, base_user_id, message_id=None):
        """نمایش گزینه‌های مدیریت OTP برای یک ادمین"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            # بررسی دسترسی
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            # دریافت اطلاعات ادمین
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            
            phone = base_user.phone_number
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            # بررسی وجود توکن‌ها
            totp_device = TOTPDevice.objects.filter(user=base_user, confirmed=True).first()
            static_device = StaticDevice.objects.filter(user=base_user, confirmed=True).first()
            
            text = f"📱 **مدیریت OTP**\n\n"
            text += f"👤 **ادمین:** {name}\n"
            text += f"📞 **شماره:** {phone}\n\n"
            text += "**وضعیت:**\n"
            text += f"🔐 TOTP: {'✅ فعال' if totp_device else '❌ غیرفعال'}\n"
            text += f"📱 Static Tokens: {'✅ فعال' if static_device else '❌ غیرفعال'}\n\n"
            
            if static_device:
                token_count = static_device.token_set.count()
                text += f"📋 **تعداد توکن‌های موجود:** {token_count}\n"
                if token_count > 0:
                    text += "\n**توکن‌های ثابت:**\n"
                    for idx, token in enumerate(static_device.token_set.all()[:5], 1):
                        text += f"{idx}. `{token.token}`\n"
            
            keyboard = [
                [InlineKeyboardButton("✨ ایجاد توکن جدید", callback_data=f"create_static_token:{base_user_id}")],
                [InlineKeyboardButton("🔄 تازه‌سازی توکن‌ها", callback_data=f"refresh_static_tokens:{base_user_id}")],
                [InlineKeyboardButton("👁️ نمایش توکن‌ها", callback_data=f"view_static_tokens:{base_user_id}")],
                [InlineKeyboardButton("🗑️ حذف تمام توکن‌ها", callback_data=f"delete_static_tokens:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="otp_menu")]
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
            
            # ذخیره‌سازی base_user_id برای استفاده بعدی
            context.user_data['otp_admin_id'] = base_user_id
        
        except Exception as e:
            logger.error(f"Error in show_admin_otp_options: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def create_static_token(chat_id, context, base_user_id, message_id=None):
        """ایجاد یک توکن ثابت جدید"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            
            # دریافت یا ایجاد StaticDevice
            device, is_new = StaticDevice.objects.get_or_create(
                user=base_user,
                defaults={'name': 'backup_codes', 'confirmed': True}
            )
            
            if not device.confirmed:
                device.confirmed = True
                device.save()
            
            # ایجاد توکن جدید
            token = ''.join(random.choices(string.digits, k=6))
            StaticToken.objects.create(device=device, token=token)
            
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            text = f"✅ **توکن جدید ایجاد شد**\n\n"
            text += f"👤 **ادمین:** {name}\n"
            text += f"📱 **توکن:** `{token}`\n\n"
            text += "⚠️ **نکات مهم:**\n"
            text += "• این توکن یک بار قابل استفاده است\n"
            text += "• پس از استفاده خودکار حذف می‌شود\n"
            text += "• برای امنیت، این توکن را ذخیره کنید"
            
            keyboard = [
                [InlineKeyboardButton("📋 نمایش تمام توکن‌ها", callback_data=f"view_static_tokens:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"otp_admin:{base_user_id}")]
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
            logger.error(f"Error in create_static_token: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def view_static_tokens(chat_id, context, base_user_id, message_id=None):
        """نمایش تمام توکن‌های ثابت"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            static_device = StaticDevice.objects.filter(user=base_user, confirmed=True).first()
            
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            text = f"📋 **توکن‌های ثابت**\n\n"
            text += f"👤 **ادمین:** {name}\n\n"
            
            if not static_device or not static_device.token_set.exists():
                text += "❌ هیچ توکنی موجود نیست"
            else:
                tokens = static_device.token_set.all()
                text += f"📱 **تعداد توکن‌ها:** {tokens.count()}\n\n"
                
                for idx, token in enumerate(tokens, 1):
                    text += f"{idx}. `{token.token}`\n"
            
            keyboard = [
                [InlineKeyboardButton("✨ ایجاد توکن جدید", callback_data=f"create_static_token:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"otp_admin:{base_user_id}")]
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
            logger.error(f"Error in view_static_tokens: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def refresh_static_tokens(chat_id, context, base_user_id, message_id=None):
        """تازه‌سازی توکن‌ها (حذف قدیمی و ایجاد جدید)"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            admin = Admin.objects.get(base_user=base_user)
            
            # دریافت یا ایجاد StaticDevice
            device, _ = StaticDevice.objects.get_or_create(
                user=base_user,
                defaults={'name': 'backup_codes', 'confirmed': True}
            )
            
            # حذف توکن‌های قدیمی
            device.token_set.all().delete()
            
            # ایجاد توکن جدید
            token = ''.join(random.choices(string.digits, k=6))
            StaticToken.objects.create(device=device, token=token)
            
            name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "بدون نام"
            
            text = f"✅ **توکن‌ها تازه‌سازی شدند**\n\n"
            text += f"👤 **ادمین:** {name}\n"
            text += f"📱 **توکن جدید:** `{token}`\n\n"
            text += "ℹ️ تمام توکن‌های قدیمی حذف شدند"
            
            keyboard = [
                [InlineKeyboardButton("📋 نمایش توکن‌ها", callback_data=f"view_static_tokens:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"otp_admin:{base_user_id}")]
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
            logger.error(f"Error in refresh_static_tokens: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
    
    @staticmethod
    async def delete_static_tokens(chat_id, context, base_user_id, message_id=None):
        """حذف تمام توکن‌های ثابت"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            
            if not AccessManager.is_allowed(user_id, 'manage_admins'):
                await context.bot.send_message(chat_id=chat_id, text="❌ دسترسی رد شد!")
                return
            
            base_user = BaseUser.objects.get(id=base_user_id)
            static_device = StaticDevice.objects.filter(user=base_user).first()
            
            if static_device:
                count = static_device.token_set.count()
                static_device.token_set.all().delete()
                
                text = f"✅ **{count} توکن حذف شدند**\n\nهیچ توکن ثابتی برای این ادمین وجود ندارد"
            else:
                text = "ℹ️ **هیچ توکنی برای حذف موجود نیست**"
            
            keyboard = [
                [InlineKeyboardButton("✨ ایجاد توکن جدید", callback_data=f"create_static_token:{base_user_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"otp_admin:{base_user_id}")]
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
            logger.error(f"Error in delete_static_tokens: {str(e)}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(e)}")
