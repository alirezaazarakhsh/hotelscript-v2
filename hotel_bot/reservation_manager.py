import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from hotel_bot.menu_manager import MenuManager
from reservation.models import Reservationhotel, ReservationRoomPassenger, Passenger

logger = logging.getLogger(__name__)

class ReservationManager:
    @staticmethod
    @database_sync_to_async
    def _get_pending_reservations_data():
        reservations = Reservationhotel.objects.filter(capacity_status='pending').select_related(
            'buyer', 'buyer__natural_profile', 'buyer__admin', 'personal_discount_code'
        ).prefetch_related(
            'reservation_rooms__room__hotel',
            'reservation_rooms__passengers'
        ).order_by('-created_at')[:10]
        
        data = []
        for res in reservations:
            res_data = {
                'tracking_code': res.tracking_code,
                'hotel_name': res.get_hotel().name if res.get_hotel() else 'نامشخص',
                'buyer_name': '',
                'buyer_phone': res.buyer.phone_number,
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
            
            # Rooms and passengers
            for rr in res.reservation_rooms.all():
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
                
                res_data['total_half_in'] += (rr.half_day_in_price or 0) * rr.quantity
                res_data['total_half_out'] += (rr.half_day_out_price or 0) * rr.quantity
            
            data.append(res_data)
        
        return data

    @staticmethod
    async def list_pending_reservations(user_id, context):
        try:
            # Get pending reservations data
            pending_reservations = await ReservationManager._get_pending_reservations_data()

            if not pending_reservations:
                text = "📋 **لیست رزروهای در انتظار تایید**\n\nهیچ رزروی در انتظار تایید وجود ندارد."
                keyboard = [[InlineKeyboardButton("بازگشت", callback_data="go_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
                return

            text = "📋 **لیست رزروهای در انتظار تایید**\n\n"
            keyboard = []

            for res in pending_reservations:
                text += f"🔹 کد پیگیری: {res['tracking_code']}\n"
                text += f"🏨 هتل: {res['hotel_name']}\n"
                text += f"👤 رزرو کننده: {res['buyer_name']} ({res['buyer_phone']})\n"
                
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
                
                text += f"💰 قیمت نهایی: {res['final_price']:,} تومان\n"
                text += f"📅 تاریخ ایجاد: {res['created_at']}\n\n"

                keyboard.append([
                    InlineKeyboardButton(f"تایید {res['tracking_code']}", callback_data=f"approve_reservation::{res['tracking_code']}"),
                    InlineKeyboardButton(f"رد {res['tracking_code']}", callback_data=f"reject_reservation::{res['tracking_code']}")
                ])

            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="go_back")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error listing pending reservations: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در نمایش لیست رزروها: {str(e)}")

    @staticmethod
    @database_sync_to_async
    def _approve_reservation_sync(tracking_code):
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

    @staticmethod
    @database_sync_to_async
    def _reject_reservation_sync(tracking_code):
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
    async def reject_reservation(user_id, context, tracking_code):
        success, message = await ReservationManager._reject_reservation_sync(tracking_code)
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")