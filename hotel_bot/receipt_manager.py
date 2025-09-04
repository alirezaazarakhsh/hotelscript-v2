from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPER_ADMINS
import json
import os

RECEIPTS_FILE = "receipts.json"  # فایل برای ذخیره رسیدهای در حال انتظار
WALLETS_FILE = "wallets.json"  # فایل برای ذخیره موجودی کیف پول کاربران

class ReceiptManager:
    @staticmethod
    def load_receipts():
        try:
            if os.path.exists(RECEIPTS_FILE):
                with open(RECEIPTS_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading receipts: {str(e)}")
            return []

    @staticmethod
    def save_receipts(receipts):
        try:
            with open(RECEIPTS_FILE, 'w') as f:
                json.dump(receipts, f)
        except Exception as e:
            print(f"Error saving receipts: {str(e)}")

    @staticmethod
    def load_wallets():
        try:
            if os.path.exists(WALLETS_FILE):
                with open(WALLETS_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading wallets: {str(e)}")
            return {}

    @staticmethod
    def save_wallets(wallets):
        try:
            with open(WALLETS_FILE, 'w') as f:
                json.dump(wallets, f)
        except Exception as e:
            print(f"Error saving wallets: {str(e)}")

    @staticmethod
    def add_receipt(user_id, amount, receipt_file_id):
        receipts = ReceiptManager.load_receipts()
        receipts.append({"user_id": user_id, "amount": amount, "receipt_file_id": receipt_file_id, "status": "pending"})
        ReceiptManager.save_receipts(receipts)

    @staticmethod
    async def show_pending_receipts(chat_id, context, message_id=None):
        try:
            receipts = ReceiptManager.load_receipts()
            pending = [r for r in receipts if r["status"] == "pending"]
            if not pending:
                text = "📜 هیچ رسید در حال انتظاری وجود ندارد."
                keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
            else:
                text = "📜 **لیست رسیدهای در حال انتظار**:\n\n"
                keyboard = []
                for idx, r in enumerate(pending):
                    text += f"{idx+1}. کاربر {r['user_id']} - مبلغ {r['amount']:,} تومان\n"
                    keyboard.append([
                        InlineKeyboardButton(f"تایید رسید {idx+1}", callback_data=f"confirm_receipt:{r['user_id']}:{r['amount']}:{idx}"),
                        InlineKeyboardButton(f"رد رسید {idx+1}", callback_data=f"reject_receipt:{r['user_id']}:{idx}")
                    ])
                keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش رسیدها: {str(e)}")

    @staticmethod
    async def confirm_receipt(context, user_id, amount, receipt_index):
        try:
            receipts = ReceiptManager.load_receipts()
            receipts[receipt_index]["status"] = "confirmed"
            ReceiptManager.save_receipts(receipts)
            # شارژ کیف پول کاربر
            wallets = ReceiptManager.load_wallets()
            wallets[str(user_id)] = wallets.get(str(user_id), 0) + amount
            ReceiptManager.save_wallets(wallets)
            await context.bot.send_message(chat_id=user_id, text=f"✅ کیف پول شما به مبلغ {amount:,} تومان شارژ شد.")
            return "✅ رسید تایید شد."
        except Exception as e:
            return f"❌ خطا در تایید رسید: {str(e)}"

    @staticmethod
    async def reject_receipt(context, user_id, receipt_index):
        try:
            receipts = ReceiptManager.load_receipts()
            receipts[receipt_index]["status"] = "rejected"
            ReceiptManager.save_receipts(receipts)
            await context.bot.send_message(chat_id=user_id, text="❌ رسید پرداخت شما رد شد. لطفاً با پشتیبانی تماس بگیرید.")
            return "✅ رسید رد شد."
        except Exception as e:
            return f"❌ خطا در رد رسید: {str(e)}"