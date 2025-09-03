from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PERMISSIONS, PERM_DISPLAY

class PermissionManager:
    @staticmethod
    async def show_group_selection(chat_id, context, admin_id, groups, message_id=None):
        if not groups:
            text = "هیچ گروه دسترسی‌ای وجود ندارد. ابتدا یک گروه ایجاد کنید.\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که می‌توانید مجوزها را به آن‌ها اختصاص دهید و سپس به ادمین‌ها割り دهید."
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="control_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            return
        text = f"انتخاب گروه دسترسی برای ادمین ID: {admin_id}\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که مجوزهای از پیش تعریف‌شده دارند. با انتخاب یک گروه، مجوزهای آن به ادمین اختصاص می‌یابد."
        keyboard = []
        row = []
        for idx, gname in enumerate(groups):
            row.append(InlineKeyboardButton(gname, callback_data=f"assign_group:{gname}:{admin_id}"))
            if (idx + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_perms")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    @staticmethod
    async def show_permissions_selection(chat_id, context, target, is_group=False, message_id=None, show_desc=False):
        selected = context.user_data.get('selected_perms', set())
        text = f"انتخاب مجوزها برای {'گروه: ' + target if is_group else 'ادمین ID: ' + str(target)}\n\nتوضیح: مجوزها دسترسی‌های خاصی را تعریف می‌کنند. می‌توانید چندین مجوز را انتخاب کنید. برای هر مجوز توضیح مختصری وجود دارد."
        if show_desc:
            for perm in PERMISSIONS:
                text += f"\n- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}"
        
        keyboard = []
        row = []
        for idx, perm in enumerate(PERMISSIONS):
            label = f"{'✅ ' if perm in selected else ''}{PERM_DISPLAY[perm]['label']}"
            callback = f"toggle_perm:{perm}:{'group' if is_group else 'admin'}"
            row.append(InlineKeyboardButton(label, callback_data=callback))
            if (idx + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("تأیید", callback_data=f"confirm_perms:{'group' if is_group else 'admin'}")])
        keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_perms")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)