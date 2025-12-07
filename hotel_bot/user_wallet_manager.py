from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from hotel_bot.config import SUPER_ADMINS
from hotel_bot.access_manager import AccessManager
from hotel_bot.receipt_manager import ReceiptManager
from hotel_bot.menu_manager import MenuManager


class UserWalletManager:
    @staticmethod
    async def prompt_for_admin_wallet_charge(chat_id, context, admin_id, message_id=None):
        try:
            if not AccessManager.is_allowed(context.user_data.get('user_id', chat_id), 'manage_wallet'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول دیگران را ندارید!")
                return
            context.user_data['state'] = 'waiting_for_admin_wallet_amount'
            context.user_data['target_admin_id'] = admin_id
            text = f"لطفاً مبلغ مورد نظر برای شارژ کیف پول ادمین {admin_id} (به تومان) را وارد کنید. حداقل 1,000,000 تومان."
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در درخواست شارژ کیف پول: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(context.user_data.get('user_id', chat_id), context)