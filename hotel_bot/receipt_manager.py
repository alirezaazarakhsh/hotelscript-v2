from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPER_ADMINS
import json
import os
import logging
from datetime import datetime
from jdatetime import datetime as jdatetime  # برای تبدیل به شمسی

# تنظیم لاگ برای دیباگ
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تنظیم مسیر فایل‌ها
RECEIPTS_FILE = os.path.join(os.getenv("PROJECT_DIR", "/app"), "receipts.json")
WALLETS_FILE = os.path.join(os.getenv("PROJECT_DIR", "/app"), "wallets.json")

class ReceiptManager:
    @staticmethod
    def load_receipts():
        """بارگذاری داده‌های رسیدها از فایل receipts.json"""
        try:
            if not os.path.exists(RECEIPTS_FILE):
                logger.warning(f"Receipts file {RECEIPTS_FILE} not found, creating an empty one")
                os.makedirs(os.path.dirname(RECEIPTS_FILE), exist_ok=True)
                with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                return {}
            
            with open(RECEIPTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded receipts from {RECEIPTS_FILE}: {data}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {RECEIPTS_FILE}: {str(e)}. Returning empty dict and attempting to fix.")
            with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            return {}
        except PermissionError as e:
            logger.error(f"Permission denied accessing {RECEIPTS_FILE}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading receipts from {RECEIPTS_FILE}: {str(e)}")
            return {}

    @staticmethod
    def save_receipts(receipts):
        """ذخیره داده‌های رسیدها در فایل receipts.json"""
        try:
            os.makedirs(os.path.dirname(RECEIPTS_FILE), exist_ok=True)
            with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(receipts, f, ensure_ascii=False, indent=4)
            logger.info(f"Receipts saved to {RECEIPTS_FILE}: {receipts}")
        except PermissionError as e:
            logger.error(f"Permission denied saving to {RECEIPTS_FILE}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error saving receipts to {RECEIPTS_FILE}: {str(e)}")
            raise

    @staticmethod
    def load_wallets():
        """بارگذاری داده‌های کیف پول‌ها از فایل wallets.json"""
        try:
            if not os.path.exists(WALLETS_FILE):
                logger.warning(f"Wallets file {WALLETS_FILE} not found, creating an empty one")
                os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
                with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                return {}
            
            with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded wallets from {WALLETS_FILE}: {data}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {WALLETS_FILE}: {str(e)}. Returning empty dict.")
            return {}
        except Exception as e:
            logger.error(f"Error loading wallets from {WALLETS_FILE}: {str(e)}")
            return {}

    @staticmethod
    def save_wallets(wallets):
        """ذخیره داده‌های کیف پول‌ها در فایل wallets.json"""
        try:
            os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
            with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(wallets, f, ensure_ascii=False, indent=4)
            logger.info(f"Wallets saved to {WALLETS_FILE}: {wallets}")
        except Exception as e:
            logger.error(f"Error saving wallets to {WALLETS_FILE}: {str(e)}")
            raise

    @staticmethod
    def get_server_time():
        """به دست آوردن زمان فعلی سرور (به وقت محلی، فرضاً تهران UTC+3:30)"""
        current_time = datetime.now()  # زمان محلی سرور
        shamsi_time = jdatetime.fromgregorian(datetime=current_time)
        return shamsi_time.strftime("%H:%M:%S - %d-%m-%Y")  # فرمت HH:MM:SS - DD-MM-YYYY

    @staticmethod
    async def add_receipt(context, user_id, amount, receipt_file_id):
        """افزودن یک رسید جدید برای کاربر و اطلاع‌رسانی به سوپرادمین‌ها"""
        try:
            logger.debug(f"Starting add_receipt: user_id={user_id}, amount={amount}, receipt_file_id={receipt_file_id}")
            user_id = str(user_id)
            if not isinstance(amount, (int, float)) or amount <= 0:
                logger.error(f"Invalid amount for user {user_id}: {amount}")
                raise ValueError("مبلغ نامعتبر است")
            if not receipt_file_id or not isinstance(receipt_file_id, str):
                logger.error(f"Invalid receipt_file_id for user {user_id}: {receipt_file_id}")
                raise ValueError("شناسه فایل رسید نامعتبر است")

            logger.debug(f"Loading receipts for user {user_id}")
            receipts = ReceiptManager.load_receipts()
            if user_id not in receipts:
                receipts[user_id] = []
            receipt_data = {
                "amount": int(amount),
                "receipt_file_id": receipt_file_id,
                "status": "pending",
                "timestamp": datetime.now().isoformat()  # زمان محلی سرور
            }
            receipts[user_id].append(receipt_data)
            logger.debug(f"Receipt data to save: {receipt_data}")
            ReceiptManager.save_receipts(receipts)
            logger.info(f"Receipt successfully added for user {user_id}: {receipt_data}")

            server_time = ReceiptManager.get_server_time()
            # ارسال پیام تأیید به کاربر (فقط یک بار)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ رسید شما برای مبلغ {amount:,} تومان با موفقیت ارسال شد و در انتظار تأیید است.\nزمان سرور: {server_time}",
                parse_mode="Markdown"
            )

            # ارسال اعلان به سوپرادمین‌ها (فقط یک بار برای هر ادمین)
            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"📥 رسید جدید از کاربر {user_id} برای مبلغ {amount:,} تومان دریافت شد.\nزمان سرور: {server_time}",
                        parse_mode="Markdown"
                    )
                    if receipt_file_id:
                        await context.bot.send_document(
                            chat_id=admin,
                            document=receipt_file_id,
                            caption=f"📎 رسید کاربر {user_id} - مبلغ {amount:,} تومان"
                        )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin}: {str(e)}")

            return True
        except ValueError as ve:
            logger.error(f"Validation error in add_receipt for user {user_id}: {str(ve)}")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ خطا در ثبت رسید: {str(ve)}",
                parse_mode="Markdown"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error in add_receipt for user {user_id}: {str(e)}")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ خطا در ثبت رسید: {str(e)}",
                parse_mode="Markdown"
            )
            raise
    

    @staticmethod
    async def show_pending_receipts(chat_id, context, message_id=None):
        """نمایش لیست رسیدهای در حال انتظار"""
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if user_id not in SUPER_ADMINS:
                logger.warning(f"User {user_id} attempted to access pending receipts without permission")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ شما مجوز مشاهده رسیدهای در حال انتظار را ندارید!",
                    parse_mode="Markdown"
                )
                from menu_manager import MenuManager
                await MenuManager.show_main_menu(user_id, context)
                return

            receipts = ReceiptManager.load_receipts()
            logger.debug(f"Loaded receipts for display: {receipts}")
            pending_receipts = []
            for uid, user_receipts in receipts.items():
                for idx, receipt in enumerate(user_receipts):
                    if receipt.get("status") == "pending":
                        pending_receipts.append((uid, idx, receipt))
            logger.debug(f"Pending receipts: {pending_receipts}")

            server_time = ReceiptManager.get_server_time()
            if not pending_receipts:
                text = "📜 **لیست رسیدهای در حال انتظار**\n\nهیچ رسید در حال انتظاری وجود ندارد.\nزمان سرور: {server_time}"
            else:
                text = "📜 **لیست رسیدهای در حال انتظار**:\n\n"
                for idx, (uid, receipt_idx, receipt) in enumerate(pending_receipts, 1):
                    timestamp = receipt.get("timestamp", "نامشخص")
                    # تبدیل تاریخ محلی به شمسی
                    if timestamp != "نامشخص":
                        local_datetime = datetime.fromisoformat(timestamp)
                        shamsi_datetime = jdatetime.fromgregorian(datetime=local_datetime)
                        formatted_time = shamsi_datetime.strftime("%H:%M:%S")
                        formatted_date = shamsi_datetime.strftime("%d-%m-%Y")
                        display_time = f"{formatted_time} - {formatted_date}"
                    else:
                        display_time = "نامشخص"
                    text += f"{idx}. کاربر {uid} - مبلغ {receipt['amount']:,} تومان - زمان: {display_time}\n"
                text += f"\nزمان سرور: {server_time}"

            keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
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
            logger.error(f"Error showing pending receipts: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش رسیدها: {str(e)}",
                parse_mode="Markdown"
            )
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def confirm_receipt(context, user_id, amount, receipt_index):
        """تأیید رسید و شارژ کیف پول کاربر"""
        try:
            user_id = str(user_id)
            receipt_index = int(receipt_index)
            if receipt_index < 0:
                logger.error(f"Invalid receipt index for user {user_id}: {receipt_index}")
                raise ValueError("شاخص رسید نامعتبر است")

            receipts = ReceiptManager.load_receipts()
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
                logger.error(f"Receipt not found for user {user_id} at index {receipt_index}")
                return "❌ رسید یافت نشد!"

            receipts[user_id][receipt_index]["status"] = "confirmed"
            ReceiptManager.save_receipts(receipts)

            amount = int(amount)
            wallets = ReceiptManager.load_wallets()
            wallets[user_id] = wallets.get(user_id, 0) + amount
            ReceiptManager.save_wallets(wallets)

            server_time = ReceiptManager.get_server_time()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ کیف پول شما به مبلغ {amount:,} تومان شارژ شد.\nزمان سرور: {server_time}",
                parse_mode="Markdown"
            )

            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"✅ رسید کاربر {user_id} برای مبلغ {amount:,} تومان تأیید شد.\nزمان سرور: {server_time}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin}: {str(e)}")

            logger.info(f"Receipt confirmed for user {user_id}: amount {amount}")
            return f"✅ رسید کاربر {user_id} برای مبلغ {amount:,} تومان تأیید شد."
        except ValueError as e:
            logger.error(f"ValueError confirming receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در تأیید رسید: {str(e)}"
        except Exception as e:
            logger.error(f"Error confirming receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در تأیید رسید: {str(e)}"

    @staticmethod
    async def reject_receipt(context, user_id, receipt_index):
        """رد رسید و اطلاع‌رسانی به کاربر"""
        try:
            user_id = str(user_id)
            receipt_index = int(receipt_index)
            if receipt_index < 0:
                logger.error(f"Invalid receipt index for user {user_id}: {receipt_index}")
                raise ValueError("شاخص رسید نامعتبر است")

            receipts = ReceiptManager.load_receipts()
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
                logger.error(f"Receipt not found for user {user_id} at index {receipt_index}")
                return "❌ رسید یافت نشد!"

            receipts[user_id][receipt_index]["status"] = "rejected"
            ReceiptManager.save_receipts(receipts)

            server_time = ReceiptManager.get_server_time()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ رسید پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.\nزمان سرور: {server_time}",
                parse_mode="Markdown"
            )

            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"❌ رسید کاربر {user_id} رد شد.\nزمان سرور: {server_time}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin}: {str(e)}")

            logger.info(f"Receipt rejected for user {user_id}")
            return f"✅ رسید کاربر {user_id} رد شد."
        except ValueError as e:
            logger.error(f"ValueError rejecting receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در رد رسید: {str(e)}"
        except Exception as e:
            logger.error(f"Error rejecting receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در رد رسید: {str(e)}"

    @staticmethod
    async def view_receipt(context, user_id, receipt_index):
        """نمایش فایل رسید برای سوپرادمین"""
        try:
            user_id = str(user_id)
            receipt_index = int(receipt_index)
            if receipt_index < 0:
                logger.error(f"Invalid receipt index for user {user_id}: {receipt_index}")
                raise ValueError("شاخص رسید نامعتبر است")

            receipts = ReceiptManager.load_receipts()
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
                logger.error(f"Receipt not found for user {user_id} at index {receipt_index}")
                return "❌ رسید یافت نشد!"

            receipt = receipts[user_id][receipt_index]
            receipt_file_id = receipt.get("receipt_file_id")
            amount = receipt.get("amount")
            status = receipt.get("status")
            timestamp = receipt.get("timestamp", "نامشخص")

            server_time = ReceiptManager.get_server_time()
            if not receipt_file_id:
                logger.error(f"No receipt file ID for user {user_id} at index {receipt_index}")
                return "❌ فایل رسید یافت نشد!"

            await context.bot.send_document(
                chat_id=context.user_data.get('user_id'),
                document=receipt_file_id,
                caption=f"📎 رسید کاربر {user_id}\nمبلغ: {amount:,} تومان\nوضعیت: {status}\nزمان: {timestamp}\nزمان سرور: {server_time}",
                parse_mode="Markdown"
            )
            logger.info(f"Receipt viewed for user {user_id}: index {receipt_index}")
            return f"✅ رسید کاربر {user_id} نمایش داده شد."
        except ValueError as e:
            logger.error(f"ValueError viewing receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در نمایش رسید: {str(e)}"
        except Exception as e:
            logger.error(f"Error viewing receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در نمایش رسید: {str(e)}"