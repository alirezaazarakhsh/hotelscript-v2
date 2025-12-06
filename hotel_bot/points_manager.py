from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from hotel_bot.config import SUPER_ADMINS
from hotel_bot.access_manager import AccessManager
import logging


# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PointsManager:
    @staticmethod
    async def show_user_points_management(query, admin_user_id, context, target_user_id):
        try:
            from authentication.models import BaseUser
            from bashgah_moshtarian.models import CustomerClubPoint
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_user_points(target_user_id):
                try:
                    user = BaseUser.objects.get(id=target_user_id)
                    points_obj, created = CustomerClubPoint.objects.get_or_create(user=user)
                    name = ""
                    if hasattr(user, 'natural_profile') and user.natural_profile:
                        name = f"{user.natural_profile.first_name or ''} {user.natural_profile.last_name or ''}".strip()
                    elif hasattr(user, 'admin') and user.admin:
                        name = f"{user.admin.first_name or ''} {user.admin.last_name or ''}".strip()
                    if not name:
                        name = user.phone_number
                    return {
                        'name': name,
                        'phone': user.phone_number,
                        'points': points_obj.points
                    }
                except BaseUser.DoesNotExist:
                    return None
            
            user_data = await get_user_points(target_user_id)
            if not user_data:
                await query.edit_message_text("❌ کاربر یافت نشد!")
                return
            
            text = f"💎 **مدیریت امتیازات باشگاه مشتریان**\n\nکاربر: {user_data['name']} ({user_data['phone']})\nامتیازات فعلی: {user_data['points']:,} امتیاز\n\nامتیازی که می‌خواهید اضافه یا کم کنید را وارد کنید (مثبت برای افزایش، منفی برای کاهش)."
            
            context.user_data['managing_points_user_id'] = target_user_id
            context.user_data['state'] = 'waiting_for_points_adjustment'
            
            keyboard = [[InlineKeyboardButton("بازگشت به لیست کاربران", callback_data="manage_points")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in show_user_points_management: {str(e)}")
            await context.bot.send_message(chat_id=admin_user_id, text=f"❌ خطا در نمایش مدیریت امتیازات: {str(e)}")