from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPER_ADMINS
from access_manager import AccessManager
from receipt_manager import ReceiptManager

class WalletManager:
    @staticmethod
    async def show_wallet_menu(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            text = "💰 **شارژ کیف پول**\n\nبرای شارژ کیف پول خود یا مشاهده موجودی، یکی از گزینه‌های زیر را انتخاب کنید. شارژ کیف پول به شما امکان استفاده از خدمات بیشتر را می‌دهد.\n\n**نکته**: حداقل مبلغ شارژ ۱,۰۰۰,۰۰۰ تومان است."
            keyboard = [
                [InlineKeyboardButton("شارژ حساب با درگاه پرداخت", callback_data="payment_gateway")],
                [InlineKeyboardButton("شارژ حساب با کارت به کارت", callback_data="card_to_card")],
                [InlineKeyboardButton("مشاهده موجودی", callback_data="view_balance")],
                [InlineKeyboardButton("بازگشت", callback_data="go_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش منوی شارژ کیف پول: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_payment_packages(chat_id, context, message_id=None):
        try:
            if not AccessManager.is_allowed(context.user_data.get('user_id', chat_id), 'wallet_charge'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول را ندارید!")
                return
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
        if not AccessManager.is_allowed(context.user_data.get('user_id', chat_id), 'wallet_charge'):
            await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول را ندارید!")
            return
        context.user_data['state'] = 'waiting_for_amount'
        await context.bot.send_message(chat_id=chat_id, text="لطفاً مبلغ مورد نظر برای شارژ (به تومان) را وارد کنید. حداقل ۱,۰۰۰,۰۰۰ تومان.")

    @staticmethod
    async def show_card_details(chat_id, context, amount, message_id=None):
        try:
            if amount < 1000000:
                raise ValueError("مبلغ کمتر از حداقل مجاز است")
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
        except ValueError as ve:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(ve)}. حداقل مبلغ ۱,۰۰۰,۰۰۰ تومان است.")
            await WalletManager.show_wallet_menu(chat_id, context)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش جزئیات کارت: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def prompt_for_receipt(chat_id, context, message_id=None):
        if not AccessManager.is_allowed(context.user_data.get('user_id', chat_id), 'wallet_charge'):
            await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول را ندارید!")
            return
        context.user_data['state'] = 'waiting_for_receipt'
        text = "📄 لطفاً رسید پرداخت را ارسال کنید (عکس یا فایل). رسید به ادمین ارسال خواهد شد."
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

    @staticmethod
    async def show_balance(chat_id, context, user_id, message_id=None):
        try:
            if not AccessManager.is_allowed(user_id, 'view_balance'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مشاهده موجودی کیف پول را ندارید!")
                return
            wallets = ReceiptManager.load_wallets()
            balance = wallets.get(str(user_id), 0)
            text = f"💰 موجودی کیف پول شما: {balance:,} تومان"
            keyboard = [
                [InlineKeyboardButton("شارژ کیف پول", callback_data="wallet_charge")],
                [InlineKeyboardButton("بازگشت ", callback_data="go_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش موجودی: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)