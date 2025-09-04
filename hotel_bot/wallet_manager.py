from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class WalletManager:
    @staticmethod
    async def show_wallet_menu(chat_id, context, message_id=None):
        try:
            text = "💰 **شارژ کیف پول**\n\nبرای شارژ کیف پول خود، یکی از روش‌های زیر را انتخاب کنید. شارژ کیف پول به شما امکان استفاده از خدمات بیشتر را می‌دهد.\n\n**نکته**: حداقل مبلغ شارژ ۱,۰۰۰,۰۰۰ تومان است."
            keyboard = [
                [InlineKeyboardButton("شارژ حساب با درگاه پرداخت", callback_data="payment_gateway")],
                [InlineKeyboardButton("شارژ حساب با کارت به کارت", callback_data="card_to_card")],
                [InlineKeyboardButton("بازگشت ", callback_data="go_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش منوی شارژ کیف پول: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(chat_id, context)

    @staticmethod
    async def show_payment_packages(chat_id, context, message_id=None):
        try:
            text = "💸 **انتخاب مبلغ برای شارژ از طریق درگاه پرداخت**\n\nلطفاً یکی از پکیج‌های زیر را انتخاب کنید. پس از انتخاب، به درگاه پرداخت هدایت می‌شوید."
            keyboard = [
                [InlineKeyboardButton("۱ میلیون تومان", callback_data="payment:1000000")],
                [InlineKeyboardButton("۲ میلیون تومان", callback_data="payment:2000000")],
                [InlineKeyboardButton("۵ میلیون تومان", callback_data="payment:5000000")],
                [InlineKeyboardButton("۱۰ میلیون تومان", callback_data="payment:10000000")],
                [InlineKeyboardButton("۲۰ میلیون تومان", callback_data="payment:20000000")],
                [InlineKeyboardButton("بازگشت", callback_data="wallet_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش پکیج‌های پرداخت: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def prompt_for_amount(chat_id, context):
        context.user_data['state'] = 'waiting_for_amount'
        await context.bot.send_message(chat_id=chat_id, text="لطفاً مبلغ مورد نظر برای شارژ (به تومان) را وارد کنید. حداقل ۱,۰۰۰,۰۰۰ تومان.")

    @staticmethod
    async def show_card_details(chat_id, context, amount, message_id=None):
        try:
            text = f"💳 **شارژ با کارت به کارت**\n\nبرای شارژ مبلغ {amount:,} تومان:\n\n**شماره کارت**: 0506-3631-1411-6362\n\nلطفاً مبلغ را به این کارت واریز کنید و رسید پرداخت را ارسال کنید (عکس یا فایل PDF)."
            keyboard = [
                [InlineKeyboardButton("ارسال رسید", callback_data="send_receipt")],
                [InlineKeyboardButton("لغو", callback_data="cancel_card_to_card")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش جزئیات کارت: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def prompt_for_receipt(chat_id, context, message_id=None):
        context.user_data['state'] = 'waiting_for_receipt'
        text = "📄 لطفاً رسید پرداخت را ارسال کنید (عکس یا فایل). رسید به ادمین ارسال خواهد شد."
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")