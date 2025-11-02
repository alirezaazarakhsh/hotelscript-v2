# reservation/signals.py
import logging
import re
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
from django.db import transaction
from threading import local
import jdatetime

from .models import (
    Reservationhotel, ReservationRoom, ReservationRoomPassenger,
    Passenger, RoomDatePrice, Room, UserCancellation, Wallet
)
from bashgah_moshtarian.models import (
    RoomDiscountCode, HotelDiscountCode, DiscountActivationRecord, CustomerClubPoint
)
from reservation.sms.sms import send_room_availability_sms
from bashgah_moshtarian.sms.sms import send_customer_club_add_sms

logger = logging.getLogger(__name__)

_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)

# ===================================================================
# 1. به‌روزرسانی موجودی اتاق هنگام رزرو (ذخیره یا حذف)
# ===================================================================
@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    room = instance.room
    with transaction.atomic():
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])
        logger.debug(f"Updated inventory for room {room.id}: {room.inventory}")

        if room.inventory == 0 and previous_inventory != 0:
            _send_zero_inventory_sms(room)

@receiver(post_delete, sender=ReservationRoom)
def update_room_inventory_on_delete(sender, instance, **kwargs):
    room = instance.room
    with transaction.atomic():
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])
        logger.debug(f"Updated inventory for room {room.id} after deletion: {room.inventory}")

        if room.inventory == 0 and previous_inventory != 0:
            _send_zero_inventory_sms(room)

# ===================================================================
# 2. وقتی دستی موجودی صفر شد (ادمین، شل، API)
# ===================================================================
@receiver(post_save, sender=Room)
def room_manual_inventory_zero_sms(sender, instance, **kwargs):
    if instance.inventory != 0:
        return

    cache_key = f"room_zero_sms_lock_{instance.pk}"
    if cache.get(cache_key):
        return

    try:
        old_instance = Room.objects.only('inventory').get(pk=instance.pk)
        if old_instance.inventory <= 0:
            return

        logger.info(f"Manual inventory zero: Room {instance.pk} ({old_instance.inventory} → 0)")
        _send_zero_inventory_sms(instance)
        cache.set(cache_key, True, timeout=60)

    except Room.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error in room_manual_inventory_zero_sms: {e}", exc_info=True)

# ===================================================================
# 3. تابع مشترک ارسال SMS موجودی صفر
# ===================================================================
def _send_zero_inventory_sms(room):
    room_name = (room.title or "اتاق").strip()
    room_full_name = f"{room_name} - آیدی {room.pk}"[:20]
    hotel_name = room.hotel.name if room.hotel and hasattr(room.hotel, 'name') else None
    status = "تکمیل"

    logger.info(f"Sending zero inventory SMS for: {room_full_name}")
    try:
        success = send_room_availability_sms(
            room_name=room_full_name,
            status=status,
            hotel_name=hotel_name,
            pattern_section='roomavailability'
        )
        if success:
            logger.info(f"SMS sent successfully: {room_full_name}")
        else:
            logger.error(f"SMS failed: {room_full_name}")
    except Exception as e:
        logger.error(f"Exception in _send_zero_inventory_sms: {e}", exc_info=True)

# ===================================================================
# 4. افزودن مسافر به دفترچه
# ===================================================================
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

    if Passenger.objects.filter(
        user=user,
        first_name=instance.first_name,
        last_name=instance.last_name,
        identification_code=identification_code
    ).exists():
        return

    try:
        Passenger.objects.create(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            phone_number=phone_number,
            identification_code=identification_code
        )
    except Exception as e:
        logger.error(f"Error creating Passenger: {e}")

# ===================================================================
# 5. به‌روزرسانی وضعیت هتل
# ===================================================================
@receiver([post_save, post_delete], sender=RoomDatePrice)
def update_hotel_status(sender, instance, **kwargs):
    hotel = instance.room.hotel
    if hotel and not hotel.has_active_date_prices():
        hotel.is_special_offer = hotel.is_flash_sale = hotel.is_best_seller = False
        hotel.save(update_fields=['is_special_offer', 'is_flash_sale', 'is_best_seller'])

# ===================================================================
# 6. مدیریت پرداخت، امتیاز، تخفیف، کیف پول - نسخه ساده‌شده
# ===================================================================
@receiver(post_save, sender=Reservationhotel)
def handle_reservation_payment_simple(sender, instance, **kwargs):
    """
    نسخه ساده‌شده برای مدیریت پرداخت رزرو
    """
    if get_skip_points_and_sms():
        logger.info(f"سیگنال برای رزرو {instance.tracking_code} نادیده گرفته شد (skip flag).")
        return

    channel_layer = get_channel_layer()

    # --- پرداخت موفق ---
    if instance.payment_status == 'paid':

        # ---------- تخصیص امتیاز ----------
        if not instance.points_assigned:
            _assign_customer_points(instance)

        # ---------- مصرف کد تخفیف ----------
        # این بخش حذف شد چون در سیگنال باشگاه مشتریان پردازش می‌شود
        # کد تخفیف زمانی مصرف می‌شود که کاربر به activated_users اضافه شود

        # ---------- برداشت از کیف پول ----------
        if instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
            _process_wallet_withdrawal(instance)

    # --- رد رزرو ---
    elif instance.capacity_status == 'rejected':
        _handle_rejected_reservation(instance)

    # --- ارسال وضعیت WebSocket ---
    _send_websocket_update(channel_layer, instance)

def _assign_customer_points(reservation):
    """تخصیص امتیاز باشگاه مشتریان"""
    cache_key = f"points_assignment_lock_{reservation.tracking_code}"
    if cache.get(cache_key):
        return

    try:
        with transaction.atomic():
            reservation_refreshed = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if reservation_refreshed.points_assigned:
                return

            cache.set(cache_key, True, timeout=60)

            total_points = sum(
                (rr.room.customer_club_points or 0) * rr.quantity
                for rr in reservation_refreshed.reservation_rooms.select_related('room').all()
            )

            if total_points > 0:
                point_obj, _ = CustomerClubPoint.objects.get_or_create(
                    user=reservation_refreshed.buyer,
                    defaults={'points': 0}
                )
                point_obj.points += total_points
                set_skip_points_and_sms(True)
                point_obj.save()
                set_skip_points_and_sms(False)

                send_customer_club_add_sms(
                    phone_number=reservation_refreshed.buyer.phone_number,
                    user_name=reservation_refreshed.buyer.get_full_name() or reservation_refreshed.buyer.phone_number,
                    added_points=total_points,
                    current_points=point_obj.points
                )
                logger.info(f"امتیاز {total_points} به {reservation_refreshed.buyer.phone_number} اضافه شد.")

            reservation_refreshed.points_assigned = True
            reservation_refreshed.save(update_fields=['points_assigned'])
            cache.delete(cache_key)

    except Exception as e:
        logger.error(f"خطا در تخصیص امتیاز برای رزرو {reservation.tracking_code}: {e}")
        cache.delete(cache_key)

def _process_wallet_withdrawal(reservation):
    """برداشت از کیف پول"""
    cache_key = f"wallet_withdrawal_lock_{reservation.tracking_code}"
    if cache.get(cache_key):
        return

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
            if wallet.balance >= reservation.wallet_withdrawal_amount:
                wallet.balance -= reservation.wallet_withdrawal_amount
                wallet.save()
                reservation.wallet_withdrawn = True
                reservation.save(update_fields=['wallet_withdrawn'])
                logger.info(f"مبلغ {reservation.wallet_withdrawal_amount} از کیف پول کسر شد.")
    except Wallet.DoesNotExist:
        logger.error(f"کیف پول برای کاربر {reservation.buyer.phone_number} یافت نشد.")
    except Exception as e:
        logger.error(f"خطا در برداشت از کیف پول: {e}")
    finally:
        cache.delete(cache_key)

def _handle_rejected_reservation(reservation):
    """مدیریت رزرو رد شده"""
    try:
        with transaction.atomic():
            for res_room in ReservationRoom.objects.filter(reservation=reservation).select_related('room'):
                room = Room.objects.select_for_update().get(pk=res_room.room.pk)
                room.revert_inventory_for_cancellation(res_room.quantity, is_auto_approved=False)
        logger.info(f"رزرو {reservation.tracking_code} رد شد → موجودی برگشت.")
    except Exception as e:
        logger.error(f"خطا در بازگشت موجودی برای رزرو رد شده {reservation.tracking_code}: {e}")

def _send_websocket_update(channel_layer, reservation):
    """ارسال به روزرسانی وضعیت از طریق WebSocket"""
    try:
        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": reservation.capacity_status,
                    "payment_status": reservation.payment_status,
                    "final_price": int(reservation.final_price) if reservation.final_price else 0,
                    "applied_discount_code": reservation.applied_discount_code,
                    "discount_processed": reservation.discount_processed,
                },
            },
        )
    except Exception as e:
        logger.error(f"خطا در ارسال WebSocket برای رزرو {reservation.tracking_code}: {e}")

# ===================================================================
# 7. مدیریت کنسلی کاربر
# ===================================================================
@receiver(post_save, sender=UserCancellation)
def handle_user_cancellation_approval(sender, instance, created, **kwargs):
    if created or instance.status != UserCancellation.Status.APPROVED:
        return

    cache_key = f"cancellation_processed_{instance.pk}"
    if cache.get(cache_key):
        return

    try:
        with transaction.atomic():
            cancellation = UserCancellation.objects.select_for_update().get(pk=instance.pk)
            reservation = Reservationhotel.objects.select_for_update().get(pk=cancellation.reservation.pk)

            if reservation.cancellation_refunded_amount > 0:
                cache.set(cache_key, True, 86400)
                return

            reservation.capacity_status = 'rejected'
            reservation.payment_status = 'unpaid'
            reservation.cancellation_requested = True

            penalty_amount, refund_amount = reservation.calculate_cancellation_refund()
            reservation.cancellation_penalty_applied = penalty_amount
            reservation.cancellation_refunded_amount = refund_amount

            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=reservation.buyer)
                wallet.balance += int(refund_amount)
                wallet.save(update_fields=['balance'])

            reservation.save(update_fields=[
                'capacity_status', 'payment_status', 'cancellation_penalty_applied',
                'cancellation_refunded_amount', 'cancellation_requested'
            ])

            cache.set(cache_key, True, 86400)
            logger.info(f"کنسلی تأیید شد: {reservation.tracking_code} | جریمه: {penalty_amount:,} | برگشتی: {refund_amount:,}")

    except Exception as e:
        logger.error(f"خطا در کنسلی {instance.pk}: {e}", exc_info=True)