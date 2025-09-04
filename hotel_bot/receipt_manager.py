from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPER_ADMINS
import json
import os
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RECEIPTS_FILE = os.path.join(os.getenv("PROJECT_DIR", "/app"), "receipts.json")  # مسیر کامل فایل
WALLETS_FILE = os.path.join(os.getenv("PROJECT_DIR", "/app"), "wallets.json")  # مسیر کامل فایل

class ReceiptManager:
    @staticmethod
    def load_receipts():
        try:
            if os.path.exists(RECEIPTS_FILE):
                with open(RECEIPTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded receipts: {data}")
                    return data
            logger.debug("Receipts file does not exist, returning empty dict")
            return {}
        except Exception as e:
            logger.error(f"Error loading receipts: {str(e)}")
            return {}

    @staticmethod
    def save_receipts(receipts):
        try:
            # اطمینان از وجود دایرکتوری
            os.makedirs(os.path.dirname(RECEIPTS_FILE), exist_ok=True)
            with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(receipts, f, ensure_ascii=False, indent=4)
            logger.debug(f"Saved receipts: {receipts}")
        except Exception as e:
            logger.error(f"Error saving receipts: {str(e)}")
            raise

    @staticmethod
    def load_wallets():
        try:
            if os.path.exists(WALLETS_FILE):
                with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded wallets: {data}")
                    return data
            logger.debug("Wallets file does not exist, returning empty dict")
            return {}
        except Exception as e:
            logger.error(f"Error loading wallets: {str(e)}")
            return {}

    @staticmethod
    def save_wallets(wallets):
        try:
            # اطمینان از وجود دایرکتوری
            os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
            with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(wallets, f, ensure_ascii=False, indent=4)
            logger.debug(f"Saved wallets: {wallets}")
        except Exception as e:
            logger.error(f"Error saving wallets: {str(e)}")
            raise

    @staticmethod
    def add_receipt(user_id, amount, receipt_file_id):
        try:
            user_id = str(user_id)  # اطمینان از رشته بودن user_id
            if not isinstance(amount, (int, float)) or amount <= 0:
                logger.error(f"Invalid amount provided for user {user_id}: {amount}")
                raise ValueError("مبلغ نامعتبر است")
            if not receipt_file_id:
                logger.error(f"Invalid receipt file ID for user {user_id}")
                raise ValueError("شناسه فایل رسید نامعتبر است")
            
            receipts = ReceiptManager.load_receipts()
            if user_id not in receipts:
                receipts[user_id] = []
            receipt_data = {
                "amount": amount,
                "receipt_file_id": receipt_file_id,
                "status": "pending"
            }
            receipts[user_id].append(receipt_data)
            ReceiptManager.save_receipts(receipts)
            logger.info(f"Receipt added for user {user_id}: {receipt_data}")
            return True
        except Exception as e:
            logger.error(f"Error adding receipt for user {user_id}: {str(e)}")
            raise  # خطا را به تابع caller منتقل می‌کنیم تا به کاربر نمایش داده شود
        

    @staticmethod
    async def show_pending_receipts(chat_id, context, message_id=None):
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
                    text += f"{idx}. کاربر {uid} - مبلغ {receipt['amount']:,} تومان\n"
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
        try:
            receipts = ReceiptManager.load_receipts()
            user_id = str(user_id)
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
                logger.error(f"Receipt not found for user {user_id} at index {receipt_index}")
                return "❌ رسید یافت نشد!"

            receipts[user_id][receipt_index]["status"] = "confirmed"
            ReceiptManager.save_receipts(receipts)

            # شارژ کیف پول کاربر
            wallets = ReceiptManager.load_wallets()
            wallets[user_id] = wallets.get(user_id, 0) + amount
            ReceiptManager.save_wallets(wallets)

            # ارسال اعلان به کاربر
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ کیف پول شما به مبلغ {amount:,} تومان شارژ شد.",
                parse_mode="Markdown"
            )

            # ارسال اعلان به تمام سوپرادمین‌ها
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
        except Exception as e:
            logger.error(f"Error confirming receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در تأیید رسید: {str(e)}"

    @staticmethod
    async def reject_receipt(context, user_id, receipt_index):
        try:
            receipts = ReceiptManager.load_receipts()
            user_id = str(user_id)
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
                logger.error(f"Receipt not found for user {user_id} at index {receipt_index}")
                return "❌ رسید یافت نشد!"

            receipts[user_id][receipt_index]["status"] = "rejected"
            ReceiptManager.save_receipts(receipts)

            # ارسال اعلان به کاربر
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ رسید پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode="Markdown"
            )

            # ارسال اعلان به تمام سوپرادمین‌ها
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
        except Exception as e:
            logger.error(f"Error rejecting receipt for user {user_id}: {str(e)}")
            return f"❌ خطا در رد رسید: {str(e)}"