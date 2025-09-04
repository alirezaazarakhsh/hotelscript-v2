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
                with open(RECEIPTS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading receipts: {str(e)}")
            return {}

    @staticmethod
    def save_receipts(receipts):
        try:
            with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(receipts, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving receipts: {str(e)}")

    @staticmethod
    def load_wallets():
        try:
            if os.path.exists(WALLETS_FILE):
                with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading wallets: {str(e)}")
            return {}

    @staticmethod
    def save_wallets(wallets):
        try:
            with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(wallets, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving wallets: {str(e)}")

    @staticmethod
    def add_receipt(user_id, amount, receipt_file_id):
        try:
            receipts = ReceiptManager.load_receipts()
            if str(user_id) not in receipts:
                receipts[str(user_id)] = []
            receipts[str(user_id)].append({
                "amount": amount,
                "receipt_file_id": receipt_file_id,
                "status": "pending"
            })
            ReceiptManager.save_receipts(receipts)
        except Exception as e:
            print(f"Error adding receipt: {str(e)}")

    @staticmethod
    async def show_pending_receipts(chat_id, context, message_id=None):
        try:
            user_id = context.user_data.get('user_id', chat_id)
            if user_id not in SUPER_ADMINS:
                await context.bot.send_message(chat_id=chat_id, text="❌ شما مجوز مشاهده رسیدهای در حال انتظار را ندارید!")
                from menu_manager import MenuManager
                await MenuManager.show_main_menu(user_id, context)
                return

            receipts = ReceiptManager.load_receipts()
            pending_receipts = []
            for uid, user_receipts in receipts.items():
                for idx, receipt in enumerate(user_receipts):
                    if receipt["status"] == "pending":
                        pending_receipts.append((uid, idx, receipt))

            if not pending_receipts:
                text = "📜 **لیست رسیدهای در حال انتظار**\n\nهیچ رسید در حال انتظاری وجود ندارد."
                keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
            else:
                text = "📜 **لیست رسیدهای در حال انتظار**:\n\n"
                keyboard = []
                for idx, (uid, receipt_idx, receipt) in enumerate(pending_receipts, 1):
                    text += f"{idx}. کاربر {uid} - مبلغ {receipt['amount']:,} تومان\n"
                    keyboard.append([
                        InlineKeyboardButton(f"تأیید رسید {idx}", callback_data=f"confirm_receipt:{uid}:{receipt['amount']}:{receipt_idx}"),
                        InlineKeyboardButton(f"رد رسید {idx}", callback_data=f"reject_receipt:{uid}:{receipt_idx}")
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
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطا در نمایش رسیدها: {str(e)}")
            from menu_manager import MenuManager
            await MenuManager.show_main_menu(user_id, context)

    @staticmethod
    async def confirm_receipt(context, user_id, amount, receipt_index):
        try:
            receipts = ReceiptManager.load_receipts()
            user_id = str(user_id)
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
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
                await context.bot.send_message(
                    chat_id=admin,
                    text=f"✅ رسید کاربر {user_id} برای مبلغ {amount:,} تومان تأیید شد.",
                    parse_mode="Markdown"
                )

            return f"✅ رسید کاربر {user_id} برای مبلغ {amount:,} تومان تأیید شد."
        except Exception as e:
            return f"❌ خطا در تأیید رسید: {str(e)}"

    @staticmethod
    async def reject_receipt(context, user_id, receipt_index):
        try:
            receipts = ReceiptManager.load_receipts()
            user_id = str(user_id)
            if user_id not in receipts or receipt_index >= len(receipts[user_id]):
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
                await context.bot.send_message(
                    chat_id=admin,
                    text=f"❌ رسید کاربر {user_id} رد شد.",
                    parse_mode="Markdown"
                )

            return f"✅ رسید کاربر {user_id} رد شد."
        except Exception as e:
            return f"❌ خطا در رد رسید: {str(e)}"