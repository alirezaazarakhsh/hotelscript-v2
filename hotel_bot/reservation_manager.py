import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from hotel_bot.menu_manager import MenuManager
from reservation.models import Reservationhotel, ReservationRoomPassenger, Passenger
from finance.models import Wallet

logger = logging.getLogger(__name__)

class ReservationManager:
    @staticmethod
    @database_sync_to_async
    def _get_all_reservations_data(page=1, per_page=5):
        offset = (page - 1) * per_page
        reservations = Reservationhotel.objects.all().select_related(
            'buyer', 'buyer__natural_profile', 'buyer__admin', 'personal_discount_code'
        ).prefetch_related(
            'reservation_rooms__room__hotel',
            'reservation_rooms__passengers'
        ).order_by('-created_at')[offset:offset + per_page]
        
        total_count = Reservationhotel.objects.count()
        total_pages = (total_count + per_page - 1) // per_page
        
        data = []
        for res in reservations:
            res_data = {
                'tracking_code': res.tracking_code,
                'capacity_status': res.capacity_status,
                'payment_status': res.payment_status,
                'hotel_name': res.get_hotel().name if res.get_hotel() else 'نامشخص',
                'buyer_name': '',
                'buyer_phone': res.buyer.phone_number,
                'wallet_balance': 0,
                'wallet_withdrawn': res.wallet_withdrawal_amount or 0,
                'rooms': [],
                'main_passenger': None,
                'other_passengers': [],
                'total_half_in': 0,
                'total_half_out': 0,
                'final_price': int(res.final_price or 0),
                'created_at': res.created_at.strftime('%Y-%m-%d %H:%M')
            }
            
            # Buyer info
            buyer = res.buyer
            if buyer.natural_profile:
                res_data['buyer_name'] = f"{buyer.natural_profile.first_name or ''} {buyer.natural_profile.last_name or ''}".strip()
            elif buyer.admin:
                res_data['buyer_name'] = f"{buyer.admin.first_name or ''} {buyer.admin.last_name or ''}".strip()
            if not res_data['buyer_name']:
                res_data['buyer_name'] = buyer.phone_number
            
            # Get wallet balance
            try:
                wallet = Wallet.objects.get(user=buyer)
                res_data['wallet_balance'] = wallet.balance
            except Wallet.DoesNotExist:
                res_data['wallet_balance'] = 0
            
            # Rooms and passengers
            for rr in res.reservation_rooms.all():
                room_name = rr.room.title if rr.room else 'نامشخص'
                res_data['rooms'].append(f"{room_name} (تعداد: {rr.quantity})")
                
                for rrp in rr.passengers.all():
                    if rrp.is_primary:
                        res_data['main_passenger'] = {
                            'name': f"{rrp.first_name} {rrp.last_name}",
                            'national_code': rrp.national_code,
                            'phone': rrp.mobile_number
                        }
                    else:
                        res_data['other_passengers'].append({
                            'name': f"{rrp.first_name} {rrp.last_name}",
                            'national_code': rrp.national_code,
                            'phone': rrp.mobile_number
                        })
                
                res_data['total_half_in'] += (rr.half_day_in_price or 0) * rr.quantity
                res_data['total_half_out'] += (rr.half_day_out_price or 0) * rr.quantity
            
            data.append(res_data)
        
        return data, total_pages, page

    @staticmethod
    async def list_all_reservations(user_id, context, page=1, per_page=5):
        try:
            # Get all reservations data with pagination
            reservations_data, total_pages, current_page = await ReservationManager._get_all_reservations_data(page, per_page)

            if not reservations_data:
                text = "📋 **لیست رزروها**\n\nاین بخش لیست همه رزروها را نمایش می‌دهد. برای هر رزرو، می‌توانید روی دکمه «مشاهده جزئیات» کلیک کنید تا اطلاعات کامل رزرو، شامل هتل، اتاق‌ها، مسافران و وضعیت پرداخت را ببینید و عملیات تایید یا رد رزرو را انجام دهید.\n\nهیچ رزروی یافت نشد."
                keyboard = [[InlineKeyboardButton("بازگشت", callback_data="go_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
                return

            text = "📋 **لیست رزروها**\n\nاین بخش لیست همه رزروها را نمایش می‌دهد. برای هر رزرو، می‌توانید روی دکمه «مشاهده جزئیات» کلیک کنید تا اطلاعات کامل رزرو، شامل هتل، اتاق‌ها، مسافران و وضعیت پرداخت را ببینید و عملیات تایید یا رد رزرو را انجام دهید.\n\n"
            keyboard = []
            message_parts = []
            current_text = text

            for i, res in enumerate(reservations_data, start=(current_page-1)*per_page + 1):
                # Create numbered button text
                button_text = f"{i}. رزرو {res['tracking_code']}"
                
                # No additional text for each reservation, just buttons
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_reservation_details::{res['tracking_code']}")])

            # Add pagination buttons if needed
            if total_pages > 1:
                pagination_buttons = []
                if current_page > 1:
                    pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"list_reservations_page::{current_page-1}"))
                if current_page < total_pages:
                    pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"list_reservations_page::{current_page+1}"))
                
                if pagination_buttons:
                    keyboard.append(pagination_buttons)
            
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
            message_parts.append((current_text, keyboard))

            # Send all parts
            for i, (msg_text, msg_keyboard) in enumerate(message_parts):
                reply_markup = InlineKeyboardMarkup(msg_keyboard) if msg_keyboard else None
                await context.bot.send_message(chat_id=user_id, text=msg_text, reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error listing all reservations: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش لیست رزروها: {str(e)}")

    @staticmethod
    @database_sync_to_async
    def _get_reservation_details(tracking_code):
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
            res_data = {
                'tracking_code': reservation.tracking_code,
                'capacity_status': reservation.capacity_status,
                'payment_status': reservation.payment_status,
                'hotel_name': reservation.get_hotel().name if reservation.get_hotel() else 'نامشخص',
                'buyer_name': '',
                'buyer_phone': reservation.buyer.phone_number,
                'wallet_balance': 0,
                'wallet_withdrawn': reservation.wallet_withdrawal_amount or 0,
                'personal_discount_used': reservation.personal_discount_used,
                'applied_discount_code': reservation.applied_discount_code,
                'half_day_in_charge': reservation.half_day_in_charge or 0,
                'half_day_out_charge': reservation.half_day_out_charge or 0,
                'rooms': [],
                'main_passenger': None,
                'other_passengers': [],
                'total_half_in': reservation.half_day_in_charge or 0,
                'total_half_out': reservation.half_day_out_charge or 0,
                'final_price': int(reservation.final_price or 0),
                'created_at': reservation.created_at.strftime('%Y-%m-%d %H:%M')
            }
            
            # Buyer info
            buyer = reservation.buyer
            if buyer.natural_profile:
                res_data['buyer_name'] = f"{buyer.natural_profile.first_name or ''} {buyer.natural_profile.last_name or ''}".strip()
            elif buyer.admin:
                res_data['buyer_name'] = f"{buyer.admin.first_name or ''} {buyer.admin.last_name or ''}".strip()
            if not res_data['buyer_name']:
                res_data['buyer_name'] = buyer.phone_number
            
            # Get wallet balance
            try:
                from finance.models import Wallet
                wallet = Wallet.objects.get(user=buyer)
                res_data['wallet_balance'] = wallet.balance
            except:
                res_data['wallet_balance'] = 0
            
            # Rooms and passengers
            for rr in reservation.reservation_rooms.all():
                room_name = rr.room.title if rr.room else 'نامشخص'
                res_data['rooms'].append(f"{room_name} (تعداد: {rr.quantity})")
                
                for rrp in rr.passengers.all():
                    if rrp.is_primary:
                        res_data['main_passenger'] = {
                            'name': f"{rrp.first_name} {rrp.last_name}",
                            'national_code': rrp.national_code
                        }
                    else:
                        res_data['other_passengers'].append({
                            'name': f"{rrp.first_name} {rrp.last_name}",
                            'national_code': rrp.national_code
                        })
            
            return res_data
        except Reservationhotel.DoesNotExist:
            return None

    @staticmethod
    async def view_reservation_details(user_id, context, tracking_code):
        try:
            res = await ReservationManager._get_reservation_details(tracking_code)
            if not res:
                await context.bot.send_message(chat_id=user_id, text=f"❌ رزرو با کد {tracking_code} یافت نشد.")
                return

            text = f"📋 **جزئیات رزرو {res['tracking_code']}**\n\n"
            text += f"🏨 هتل: {res['hotel_name']}\n"
            text += f"👤 رزرو کننده: {res['buyer_name']} ({res['buyer_phone']})\n"
            text += f"💰 موجودی کیف پول: {res['wallet_balance']:,} تومان\n"
            if res['wallet_withdrawn'] > 0:
                text += f"💸 برداشت از کیف پول: {res['wallet_withdrawn']:,} تومان\n"
            
            # Rooms
            text += "🏠 اتاق‌ها:\n"
            for room in res['rooms']:
                text += f"  - {room}\n"
            
            # Passengers
            if res['main_passenger']:
                mp = res['main_passenger']
                text += f"🧑 مسافر اصلی: {mp['name']} ({mp['national_code']})\n"
            
            if res['other_passengers']:
                text += "👥 مسافران دیگر:\n"
                for p in res['other_passengers']:
                    text += f"  - {p['name']} ({p['national_code']})\n"
            
            # Room info with half charges
            if res['total_half_in'] > 0 or res['total_half_out'] > 0:
                text += f"🏠 نیم شارژ ورود: {int(res['total_half_in']):,} تومان\n"
                text += f"🏠 نیم شارژ خروج: {int(res['total_half_out']):,} تومان\n"
            
            text += f"📅 تاریخ ایجاد: {res['created_at']}\n"
            text += f"📊 وضعیت ظرفیت: {dict(Reservationhotel.CAPACITY_STATUS_CHOICES).get(res['capacity_status'], res['capacity_status'])}\n"
            text += f"💳 وضعیت پرداخت: {dict(Reservationhotel.PAYMENT_STATUS_CHOICES).get(res['payment_status'], res['payment_status'])}\n"
            
            # Payment details
            text += "💳 **جزئیات پرداخت**:\n"
            if res['personal_discount_used']:
                text += f"  - کد تخفیف شخصی استفاده شده\n"
            if res['applied_discount_code']:
                text += f"  - کد تخفیف: {res['applied_discount_code']}\n"
            if res['half_day_in_charge'] > 0:
                text += f"  - نیم شارژ ورود: {int(res['half_day_in_charge']):,} تومان\n"
            if res['half_day_out_charge'] > 0:
                text += f"  - نیم شارژ خروج: {int(res['half_day_out_charge']):,} تومان\n"
            if res['wallet_withdrawn'] > 0:
                text += f"  - برداشت از کیف پول: {res['wallet_withdrawn']:,} تومان\n"
            
            text += f"💰 قیمت نهایی: {res['final_price']:,} تومان\n"

            # Buttons based on status
            buttons = []
            if res['capacity_status'] == 'pending':
                buttons.append(InlineKeyboardButton(f"تایید", callback_data=f"approve_reservation::{res['tracking_code']}"))
                buttons.append(InlineKeyboardButton(f"رد", callback_data=f"reject_reservation::{res['tracking_code']}"))
            elif res['capacity_status'] == 'confirmed':
                buttons.append(InlineKeyboardButton(f"رد", callback_data=f"reject_reservation::{res['tracking_code']}"))
                buttons.append(InlineKeyboardButton(f"به انتظار", callback_data=f"pending_reservation::{res['tracking_code']}"))
            elif res['capacity_status'] == 'rejected':
                buttons.append(InlineKeyboardButton(f"تایید", callback_data=f"approve_reservation::{res['tracking_code']}"))
                buttons.append(InlineKeyboardButton(f"به انتظار", callback_data=f"pending_reservation::{res['tracking_code']}"))
            
            keyboard = [buttons, [InlineKeyboardButton("بازگشت به لیست", callback_data="view_reservations")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error viewing reservation details: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش جزئیات رزرو: {str(e)}")

    @staticmethod
    @database_sync_to_async
    def _approve_reservation_sync(tracking_code):
        from reservation.models import set_skip_points_and_sms
        set_skip_points_and_sms(True)
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
            if reservation.capacity_status != 'pending':
                return False, f"❌ رزرو {tracking_code} قبلاً پردازش شده است."
            reservation.capacity_status = 'confirmed'
            reservation.save(update_fields=['capacity_status'])
            return True, f"✅ رزرو {tracking_code} با موفقیت تایید شد."
        except Reservationhotel.DoesNotExist:
            return False, f"❌ رزرو با کد {tracking_code} یافت نشد."
        except Exception as e:
            logger.error(f"Error approving reservation {tracking_code}: {e}")
            return False, f"❌ خطا در تایید رزرو: {str(e)}"

    @staticmethod
    async def approve_reservation(user_id, context, tracking_code):
        success, message = await ReservationManager._approve_reservation_sync(tracking_code)
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        
        if success:
            # Notify super admins
            from hotel_bot.config import SUPER_ADMINS
            notification_text = f"✅ رزرو {tracking_code} توسط ادمین تایید شد."
            for admin_id in SUPER_ADMINS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=notification_text, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")

    @staticmethod
    @database_sync_to_async
    def _reject_reservation_sync(tracking_code):
        from reservation.models import set_skip_points_and_sms
        set_skip_points_and_sms(True)
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
            if reservation.capacity_status != 'pending':
                return False, f"❌ رزرو {tracking_code} قبلاً پردازش شده است."
            reservation.capacity_status = 'rejected'
            reservation.save(update_fields=['capacity_status'])
            return True, f"❌ رزرو {tracking_code} رد شد."
        except Reservationhotel.DoesNotExist:
            return False, f"❌ رزرو با کد {tracking_code} یافت نشد."
        except Exception as e:
            logger.error(f"Error rejecting reservation {tracking_code}: {e}")
            return False, f"❌ خطا در رد رزرو: {str(e)}"

    @staticmethod
    @database_sync_to_async
    def _pending_reservation_sync(tracking_code):
        from reservation.models import set_skip_points_and_sms
        set_skip_points_and_sms(True)
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
            reservation.capacity_status = 'pending'
            reservation.save(update_fields=['capacity_status'])
            return True, f"✅ رزرو {tracking_code} به وضعیت در انتظار تغییر یافت."
        except Reservationhotel.DoesNotExist:
            return False, f"❌ رزرو با کد {tracking_code} یافت نشد."
        except Exception as e:
            logger.error(f"Error setting reservation to pending {tracking_code}: {e}")
            return False, f"❌ خطا در تغییر وضعیت رزرو: {str(e)}"

    @staticmethod
    async def pending_reservation(user_id, context, tracking_code):
        success, message = await ReservationManager._pending_reservation_sync(tracking_code)
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")