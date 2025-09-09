from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from hotel_bot.config import PERM_DISPLAY


class GroupManager:
    @staticmethod
    async def show_manage_groups(chat_id, context, groups, message_id=None):
        try:
            if not isinstance(groups, dict):
                raise ValueError("آرگومان groups باید یک دیکشنری باشد")
            
            if not groups:
                text = "هیچ گروه دسترسی‌ای وجود ندارد.\n\nتوضیح: گروه‌های دسترسی نقش‌هایی هستند که می‌توانید مجوزها را به آن‌ها اختصاص دهید و سپس به ادمین‌ها اختصاص دهید."
                keyboard = [[InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")]]
            else:
                text = "لیست گروه‌های دسترسی:\n\nتوضیح: می‌توانید هر گروه را ویرایش، حذف یا مجوزهای آن را مشاهده کنید."
                keyboard = []
                row = []
                for idx, gname in enumerate(groups):
                    if not isinstance(gname, str):
                        continue  # نادیده گرفتن کلیدهای نامعتبر
                    row.append(InlineKeyboardButton(gname, callback_data=f"view_group:{gname}"))
                    if (idx + 1) % 2 == 0:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("بازگشت به کنترل پنل", callback_data="control_panel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش لیست گروه‌ها: {str(e)}"
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )

    @staticmethod
    async def show_group_details(chat_id, context, group_name, groups, message_id=None):
        try:
            if not isinstance(groups, dict) or not isinstance(group_name, str):
                raise ValueError("ورودی‌های نامعتبر برای نمایش جزئیات گروه")
            
            perms = groups.get(group_name, set())
            text = f"جزئیات گروه: {group_name}\n\nمجوزها:\n"
            for perm in perms:
                if perm in PERM_DISPLAY:
                    text += f"- {PERM_DISPLAY[perm]['label']}: {PERM_DISPLAY[perm]['desc']}\n"
                else:
                    text += f"- {perm}: (بدون توضیح)\n"
            if not perms:
                text += "هیچ مجوزی اختصاص نیافته.\n"
            text += "\nتوضیح: می‌توانید مجوزها را ویرایش کنید، نام گروه را تغییر دهید یا گروه را حذف کنید."
            
            keyboard = [
                [
                    InlineKeyboardButton("ویرایش مجوزها", callback_data=f"edit_group_perms:{group_name}"),
                    InlineKeyboardButton("تغییر نام", callback_data=f"rename_group:{group_name}")
                ],
                [
                    InlineKeyboardButton("حذف گروه", callback_data=f"delete_group:{group_name}"),
                    InlineKeyboardButton("بازگشت", callback_data="manage_groups")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در نمایش جزئیات گروه: {str(e)}"
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )