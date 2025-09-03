from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PERM_DISPLAY
from access_manager import AccessManager

class AdminManager:
    @staticmethod
    async def show_manage_admins(chat_id, context, admins, message_id=None):
        if not admins:
            text = "هیچ ادمینی وجود ندارد.\n\nتوضیح: می‌توانید ادمین‌های جدید اضافه کنید یا گروه‌های دسترسی را مدیریت کنید."
            keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
        else:
            text = "لیست ادمین‌ها:\n\nتوضیح: می‌توانید هر ادمین را ویرایش یا حذف کنید."
            keyboard = []
            row = []
            for idx, uid in enumerate(admins):
                row.append(InlineKeyboardButton(f"ID: {uid}", callback_data=f"view_admin:{uid}"))
                if (idx + 1) % 2 == 0:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    @staticmethod
    async def show_admin_details(chat_id, context, admin_id, admins, groups, message_id=None):
        group = admins.get(admin_id)
        perms = groups.get(group, set()) if group else set()
        text = f"جزئیات ادمین ID: {admin_id}\n\nگروه دسترسی: {group or 'هیچ'}\n\nمجوزها:\n"
        for perm in perms:
            text += f"- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}\n"
        if not perms:
            text += "هیچ مجوزی اختصاص نیافته.\n"
        text += "\nتوضیح: می‌توانید گروه دسترسی این ادمین را تغییر دهید یا ادمین را حذف کنید."
        
        keyboard = [
            [InlineKeyboardButton("تغییر گروه دسترسی", callback_data=f"assign_group_menu:{admin_id}")],
            [InlineKeyboardButton("حذف ادمین", callback_data=f"delete_admin:{admin_id}"),
             InlineKeyboardButton("بازگشت", callback_data="manage_admins")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)