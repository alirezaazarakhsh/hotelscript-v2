import logging
import re
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
from django.db import transaction
from threading import local
import jdatetime
import traceback

from .models import (
    Reservationhotel, ReservationRoom, ReservationRoomPassenger,
    Passenger, RoomDatePrice, Room, UserCancellation
)
from finance.models import Wallet
from bashgah_moshtarian.models import (
    RoomDiscountCode, HotelDiscountCode, DiscountActivationRecord, CustomerClubPoint, PersonalDiscountCode
)
from reservation.sms.sms import send_room_availability_sms
from bashgah_moshtarian.sms.sms import send_customer_club_add_sms

logger = logging.getLogger(__name__)

_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)


@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    room = instance.room
    with transaction.atomic():
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])

        if room.inventory == 0 and previous_inventory != 0:
            _send_zero_inventory_sms(room)


def _send_zero_inventory_sms(room):
    room_full_name = f"{(room.title or 'اتاق')[:15]} - ID {room.pk}"
    hotel_name = room.hotel.name if room.hotel else None
    try:
        send_room_availability_sms(
            room_name=room_full_name,
            status="تکمیل",
            hotel_name=hotel_name,
            pattern_section='roomavailability'
        )
    except Exception as e:
        logger.error(f"Exception in _send_zero_inventory_sms: {e}")


@receiver(post_save, sender=ReservationRoomPassenger)
def add_to_passenger_book(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        user = instance.reservation_room.reservation.buyer
        if not user:
            return
    except AttributeError:
        return

    phone_number = instance.mobile_number
    identification_code = instance.national_code

    if instance.passenger_type == 'primary':
        if not identification_code or not phone_number or not re.match(r'^09\d{9}$', phone_number):
            return
    else:
        phone_number = phone_number if phone_number and re.match(r'^09\d{9}$', phone_number) else '09123456789'
        identification_code = identification_code or f"{instance.first_name}_{instance.last_name}_temp"[:10]

    if not Passenger.objects.filter(user=user, identification_code=identification_code).exists():
        try:
            Passenger.objects.create(
                user=user,
                first_name=instance.first_name,
                last_name=instance.last_name,
                phone_number=phone_number,
                identification_code=identification_code
            )
        except Exception:
            pass


@receiver(post_save, sender=Reservationhotel)
def handle_reservation_payment_complete(sender, instance, **kwargs):
    """
    مدیریت پرداخت و تایید قطعی در اسنپ و ارسال وضعیت به وب‌سوکت
    """
    channel_layer = get_channel_layer()

    # ۱. اگر پرداخت انجام شد
    if instance.payment_status == 'paid':
        # بررسی کیف پول اسنپ و تایید در وب‌سرویس اسنپ
        if instance.is_snapptrip_reservation and instance.snapp_reservation_code and instance.snapp_status != 'confirmed':
            from reservation.snapptrip_service import process_payment_and_confirm_snapp
            success_snapp, msg_snapp = process_payment_and_confirm_snapp(instance)
            if not success_snapp:
                # کیف پول اسنپ شارژ نداشت: رزرو ریجکت شده و پیام به فرانت ارسال می‌شود
                instance.refresh_from_db()
                _send_websocket_update(channel_layer, instance, custom_message=msg_snapp)
                return

        # کسر از کیف پول محلی کاربر
        if instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
            _process_wallet_withdrawal(instance)

        # مصرف کد تخفیف
        if instance.applied_discount_code and not instance.discount_processed:
            _process_discount_code(instance)

        # تخصیص امتیاز
        if not instance.points_assigned:
            _assign_customer_points(instance)

    # ۲. ارسال وضعیت به وب‌سوکت (چه بعد از تایید ادمین و چه بعد از تایید اسنپ)
    _send_websocket_update(channel_layer, instance)


def _process_wallet_withdrawal(reservation):
    """کسر مطمئن از کیف پول کاربر"""
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if res.wallet_withdrawn or res.wallet_withdrawal_amount <= 0:
                return True
            wallet = Wallet.objects.select_for_update().get(user=res.buyer)
            amount = int(res.wallet_withdrawal_amount)
            if wallet.balance >= amount:
                wallet.balance = F('balance') - amount
                wallet.save(update_fields=['balance'])
                Reservationhotel.objects.filter(pk=res.pk).update(wallet_withdrawn=True)
                return True
            return False
    except Exception as e:
        logger.error(f"خطا در کسر کیف پول کاربر: {e}")
        return False


def _assign_customer_points(reservation):
    """تخصیص امتیاز باشگاه مشتریان"""
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if res.points_assigned:
                return True
            total_points = sum(
                (rr.room.customer_club_points or 0) * rr.quantity
                for rr in res.reservation_rooms.select_related('room').all()
            )
            if total_points > 0:
                p_obj, _ = CustomerClubPoint.objects.get_or_create(user=res.buyer, defaults={'points': 0})
                p_obj.points += total_points
                p_obj.save(update_fields=['points'])
            Reservationhotel.objects.filter(pk=res.pk).update(points_assigned=True)
            return True
    except Exception as e:
        logger.error(f"خطا در تخصیص امتیاز: {e}")
        return False


def _process_discount_code(reservation):
    """مصرف کد تخفیف"""
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if res.discount_processed:
                return True
            Reservationhotel.objects.filter(pk=res.pk).update(discount_processed=True)
            return True
    except Exception as e:
        logger.error(f"خطا در مصرف کد تخفیف: {e}")
        return False


def _send_websocket_update(channel_layer, reservation, custom_message=None):
    """ارسال به روزرسانی وضعیت از طریق WebSocket همراه با موجودی کیف پول کاربر"""
    try:
        user_wallet = getattr(reservation.buyer, 'wallet', None)
        user_balance = int(user_wallet.balance) if user_wallet else 0

        # اگر وضعیت رزرو confirmed باشد، تایمر ۱۵ دقیقه برای پرداخت فرانت ارسال می‌شود
        timer_val = 900 if reservation.capacity_status == 'confirmed' and reservation.payment_status != 'paid' else None

        msg = {
            "capacity_status": reservation.capacity_status,
            "payment_status": reservation.payment_status,
            "snapp_status": reservation.snapp_status,
            "final_price": int(reservation.final_price) if reservation.final_price else 0,
            "wallet_balance": user_balance,
            "timer": timer_val
        }
        if custom_message:
            msg["error_reason"] = custom_message

        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": msg,
            },
        )
    except Exception as e:
        logger.error(f"خطا در ارسال به وب‌سوکت: {e}")