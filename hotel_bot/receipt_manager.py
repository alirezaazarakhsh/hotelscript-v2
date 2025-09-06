from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPER_ADMINS
import json
import os
import logging
from datetime import datetime
from telegram.error import BadRequest
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
    async def add_receipt(context, user_id, amount, receipt_file_id, is_photo=False):
        """افزودن یک رسید جدید برای کاربر و اطلاع‌رسانی به سوپرادمین‌ها"""
        try:
            logger.debug(f"Starting add_receipt: user_id={user_id}, amount={amount}, receipt_file_id={receipt_file_id}, is_photo={is_photo}")
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
                "file_type": "photo" if is_photo else "document",
                "status": "pending",
                "timestamp": datetime.utcnow().isoformat()
            }
            receipts[user_id].append(receipt_data)
            logger.debug(f"Receipt data to save: {receipt_data}")
            ReceiptManager.save_receipts(receipts)
            logger.info(f"Receipt successfully added for user {user_id}: {receipt_data}")

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ رسید شما برای مبلغ {amount:,} تومان با موفقیت ارسال شد و در انتظار تأیید است.",
                parse_mode="Markdown"
            )

            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"📥 رسید جدید از کاربر {user_id} برای مبلغ {amount:,} تومان دریافت شد.",
                        parse_mode="Markdown"
                    )
                    if is_photo:
                        await context.bot.send_photo(
                            chat_id=admin,
                            photo=receipt_file_id,
                            caption=f"📎 رسید کاربر {user_id} - مبلغ {amount:,} تومان",
                            parse_mode="Markdown"
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=admin,
                            document=receipt_file_id,
                            caption=f"📎 رسید کاربر {user_id} - مبلغ {amount:,} تومان",
                            parse_mode="Markdown"
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

            if not pending_receipts:
                text = "📜 **لیست رسیدهای در حال انتظار**\n\nهیچ رسید در حال انتظاری وجود ندارد."
                keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
            else:
                text = "📜 **لیست رسیدهای در حال انتظار**:\n\n"
                keyboard = []
                for idx, (uid, receipt_idx, receipt) in enumerate(pending_receipts, 1):
                    timestamp = receipt.get("timestamp", "نامشخص")
                    if timestamp != "نامشخص":
                        try:
                            local_datetime = datetime.fromisoformat(timestamp)
                            shamsi_datetime = jdatetime.fromgregorian(datetime=local_datetime)
                            formatted_time = shamsi_datetime.strftime("%H:%M:%S - %Y/%m/%d")
                        except ValueError:
                            formatted_time = "نامشخص"
                    else:
                        formatted_time = "نامشخص"
                    text += f"{idx}. کاربر {uid} - مبلغ {receipt['amount']:,} تومان - زمان: {formatted_time}\n"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"تأیید رسید {idx}",
                            callback_data=f"confirm_receipt:{uid}:{receipt['amount']}:{receipt_idx}"
                        ),
                        InlineKeyboardButton(
                            f"رد رسید {idx}",
                            callback_data=f"reject_receipt:{uid}:{receipt_idx}"
                        ),
                        InlineKeyboardButton(
                            f"مشاهده رسید {idx}",
                            callback_data=f"view_receipt:{uid}:{receipt_idx}"
                        )
                    ])
                keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

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

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ کیف پول شما به مبلغ {amount:,} تومان شارژ شد.",
                parse_mode="Markdown"
            )

            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"✅ رسید کاربر {user_id} برای مبلغ {amount:,} تومان تأیید شد.",
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

            await context.bot.send_message(
                chat_id=user_id,
                text="❌ رسید پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode="Markdown"
            )

            for admin in SUPER_ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"❌ رسید کاربر {user_id} رد شد.",
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
    async def view_receipt(context, user_id, receipt_index, chat_id=None):
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
            file_type = receipt.get("file_type", "photo")  # پیش‌فرض photo برای رسیدهای قدیمی

            if not receipt_file_id or not isinstance(receipt_file_id, str):
                logger.error(f"Invalid receipt_file_id for user {user_id}: {receipt_file_id}")
                return "❌ شناسه فایل رسید نامعتبر است!"

            # تبدیل زمان به شمسی
            if timestamp != "نامشخص":
                try:
                    local_datetime = datetime.fromisoformat(timestamp)
                    shamsi_datetime = jdatetime.fromgregorian(datetime=local_datetime)
                    formatted_time = shamsi_datetime.strftime("%H:%M:%S - %Y/%m/%d")
                except ValueError:
                    formatted_time = "نامشخص"
            else:
                formatted_time = "نامشخص"

            # استفاده از chat_id ارسالی یا از context
            target_chat_id = chat_id or context.user_data.get('user_id')
            if not target_chat_id:
                logger.error(f"No valid chat_id provided for user {user_id}")
                return "❌ خطا: شناسه چت معتبر نیست!"

            caption = f"📎 رسید کاربر {user_id}\nمبلغ: {amount:,} تومان\nوضعیت: {status}\nزمان: {formatted_time}"
            logger.debug(f"Attempting to send file with ID: {receipt_file_id}, type: {file_type} to chat_id: {target_chat_id}")

            try:
                if file_type == "photo":
                    await context.bot.send_photo(
                        chat_id=target_chat_id,
                        photo=receipt_file_id,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_document(
                        chat_id=target_chat_id,
                        document=receipt_file_id,
                        caption=caption,
                        parse_mode="Markdown"
                    )
            except BadRequest as e:
                logger.error(f"BadRequest error sending file {receipt_file_id}: {str(e)}")
                # اگر ارسال به صورت photo شکست خورد، به صورت document امتحان می‌کنیم
                if file_type == "photo":
                    logger.debug(f"Retrying to send file {receipt_file_id} as document")
                    await context.bot.send_document(
                        chat_id=target_chat_id,
                        document=receipt_file_id,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                else:
                    raise

            logger.info(f"Receipt viewed for user {user_id}: index {receipt_index}")
            return f"✅ رسید کاربر {user_id} نمایش داده شد."
        except BadRequest as e:
            logger.error(f"BadRequest error sending file {receipt_file_id}: {str(e)}")
            return f"❌ خطا در ارسال فایل رسید: فایل در سرور تلگرام در دسترس نیست."
        except ValueError as e:
            logger.error(f"ValueError viewing receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در نمایش رسید: {str(e)}"
        except Exception as e:
            logger.error(f"Error viewing receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در نمایش رسید: {str(e)}"