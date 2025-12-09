from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from hotel_bot.config import SUPER_ADMINS
from hotel_bot.access_manager import AccessManager
from hotel_bot.receipt_manager import ReceiptManager
from hotel_bot.menu_manager import MenuManager
from finance.models import Wallet
from asgiref.sync import sync_to_async
import logging


# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletManager:
    @staticmethod
    async def show_wallet_menu(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            text = "💰 **شارژ کیف پول**\n\nبرای شارژ کیف پول خود یا مشاهده موجودی، یکی از گزینه‌های زیر را انتخاب کنید. شارژ کیف پول به شما امکان استفاده از خدمات بیشتر را می‌دهد.\n\n**نکته**: حداقل مبلغ شارژ 1,000,000 تومان است."
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
            logger.error(f"Error in show_wallet_menu: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش منوی شارژ کیف پول: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_payment_packages(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'wallet_charge'):
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
            logger.error(f"Error in show_payment_packages: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش پکیج‌های پرداخت: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def prompt_for_amount(chat_id, context):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'wallet_charge'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول را ندارید!")
                return
            context.user_data['state'] = 'waiting_for_amount'
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً مبلغ مورد نظر برای شارژ (به تومان) را وارد کنید. حداقل 1,000,000 تومان.",
                parse_mode="Markdown"
            )
            logger.debug(f"Prompted user {user_id} for amount")
        except Exception as e:
            logger.error(f"Error in prompt_for_amount: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در درخواست مبلغ: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def show_card_details(chat_id, context, amount, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if amount < 1000000:
                raise ValueError("مبلغ کمتر از حداقل مجاز است")
            context.user_data['amount'] = amount  # ذخیره مبلغ در context
            text = (
                f"💳 **شارژ با کارت به کارت**\n\n"
                f"برای شارژ مبلغ {amount:,} تومان:\n\n"
                f"**شماره کارت**: 0506-3631-1411-6362\n\n"    
                f"**شماره شبا**: IR760620000000203839567007\n\n"      
                f"** نام صاحب حساب**: علیرضا آذرخش آلوچه\n\n"
                f"لطفاً مبلغ را به این شماره کارت یا شماره شبا واریز کنید و رسید پرداخت را ارسال کنید و پس از برسی و تایید شما حساب شما به صورت خودکار شارژ خواهد شد(عکس یا فایل PDF)."
            )
            keyboard = [
                [InlineKeyboardButton("ارسال رسید", callback_data="send_receipt")],
                [InlineKeyboardButton("لغو", callback_data="cancel_card_to_card")]
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
            logger.debug(f"Displayed card details for user {user_id}, amount: {amount}")
        except ValueError as ve:
            logger.error(f"ValueError in show_card_details: {str(ve)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا: {str(ve)}. حداقل مبلغ ۱,۰۰۰,۰۰۰ تومان است.")
            await WalletManager.show_wallet_menu(chat_id, context)
        except Exception as e:
            logger.error(f"Error in show_card_details: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش جزئیات کارت: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def prompt_for_receipt(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if not AccessManager.is_allowed(user_id, 'wallet_charge'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز شارژ کیف پول را ندارید!")
                return
            context.user_data['state'] = 'waiting_for_receipt'
            text = "📄 لطفاً رسید پرداخت را ارسال کنید (عکس یا فایل PDF). رسید به ادمین ارسال خواهد شد."
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown"
                )
            logger.debug(f"Prompted user {user_id} for receipt")
        except Exception as e:
            logger.error(f"Error in prompt_for_receipt: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در درخواست رسید: {str(e)}")
            await WalletManager.show_wallet_menu(chat_id, context)

    @staticmethod
    async def show_balance(chat_id, context, user_id, message_id=None):
        try:
            if not AccessManager.is_allowed(user_id, 'view_balance'):
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مشاهده موجودی کیف پول را ندارید!")
                return
            balance = await WalletManager.get_balance(user_id)
            text = f"💰 موجودی کیف پول شما: {balance:,} تومان"
            keyboard = [
                [InlineKeyboardButton("شارژ کیف پول", callback_data="wallet_charge")],
                [InlineKeyboardButton("بازگشت", callback_data="go_back")]
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
            logger.debug(f"Displayed balance for user {user_id}: {balance}")
        except Exception as e:
            logger.error(f"Error in show_balance: {str(e)}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش موجودی: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def show_user_wallet_management(query, admin_user_id, context, target_user_id):
        try:
            from authentication.models import BaseUser
            from finance.models import Wallet
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_user_wallet(target_user_id):
                try:
                    user = BaseUser.objects.get(id=target_user_id)
                    wallet, created = Wallet.objects.get_or_create(user=user)
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
                        'balance': wallet.balance
                    }
                except BaseUser.DoesNotExist:
                    return None
            
            user_data = await get_user_wallet(target_user_id)
            if not user_data:
                await query.edit_message_text("❌ کاربر یافت نشد!")
                return
            
            text = f"💰 **مدیریت کیف پول کاربر**\n\nکاربر: {user_data['name']} ({user_data['phone']})\nموجودی فعلی: {user_data['balance']:,} تومان\n\nمبلغی که می‌خواهید اضافه یا کم کنید را وارد کنید (مثبت برای افزایش، منفی برای کاهش)."
            
            context.user_data['managing_wallet_user_id'] = target_user_id
            context.user_data['state'] = 'waiting_for_wallet_adjustment'
            
            keyboard = [[InlineKeyboardButton("بازگشت به لیست کاربران", callback_data="manage_wallet")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in show_user_wallet_management: {str(e)}")
            await context.bot.send_message(chat_id=admin_user_id, text=f"❌ خطا در نمایش مدیریت کیف پول: {str(e)}")

    @staticmethod
    async def get_balance(user_id):
        try:
            wallet = await sync_to_async(Wallet.objects.get)(user=user_id)
            return wallet.balance
        except Wallet.DoesNotExist:
            return 0

    @staticmethod
    async def deduct_balance(user_id, amount):
        try:
            wallet = await sync_to_async(Wallet.objects.get)(user=user_id)
            if wallet.balance >= amount:
                wallet.balance -= amount
                await sync_to_async(wallet.save)()
                return True
            return False
        except Wallet.DoesNotExist:
            return False

    @staticmethod
    async def charge_balance(user_id, amount):
        try:
            wallet, created = await sync_to_async(Wallet.objects.get_or_create)(user=user_id, defaults={'balance': 0})
            wallet.balance += amount
            await sync_to_async(wallet.save)()
            return True
        except Exception:
            return False