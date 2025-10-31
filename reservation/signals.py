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
from .models import (
    Reservationhotel, ReservationRoom, ReservationRoomPassenger, 
    Passenger, RoomDatePrice, Room, UserCancellation, Wallet
)
from bashgah_moshtarian.models import (
    RoomDiscountCode, HotelDiscountCode, DiscountActivationRecord, CustomerClubPoint
)
from reservation.sms.sms import send_room_availability_sms
from bashgah_moshtarian.sms.sms import send_customer_club_add_sms
import jdatetime

logger = logging.getLogger(__name__)

# متغیر محلی برای کنترل ارسال SMS و تخصیص امتیاز
_thread_locals = local()

def set_skip_points_and_sms(value):
    """تنظیم فلگ برای جلوگیری از تخصیص امتیاز و ارسال SMS در یک درخواست."""
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    """دریافت وضعیت فلگ تخصیص امتیاز و ارسال SMS."""
    return getattr(_thread_locals, 'skip_points_and_sms', False)


# ===================================================================
# 1. به‌روزرسانی موجودی اتاق هنگام رزرو (ذخیره یا حذف)
# ===================================================================
@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    """
    به‌روزرسانی موجودی اتاق هنگام ذخیره یا ویرایش رزرو اتاق و ارسال پیامک در صورت صفر شدن موجودی.
    """
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
    """
    به‌روزرسانی موجودی اتاق هنگام حذف رزرو اتاق و ارسال پیامک در صورت صفر شدن موجودی.
    """
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
# 2. سیگنال جدید: وقتی دستی موجودی صفر شد (ادمین، شل، API)
# ===================================================================
@receiver(post_save, sender=Room)
def room_manual_inventory_zero_sms(sender, instance, **kwargs):
    """
    وقتی موجودی اتاق دستی از مثبت به صفر رسید، SMS بفرست.
    (مستقل از رزروها)
    """
    if instance.inventory != 0:
        return

    cache_key = f"room_zero_sms_lock_{instance.pk}"
    if cache.get(cache_key):
        return  # قبلاً در 60 ثانیه SMS رفته

    try:
        old_instance = Room.objects.only('inventory').get(pk=instance.pk)
        if old_instance.inventory <= 0:
            return  # قبلاً صفر بوده

        logger.info(f"Manual inventory zero: Room {instance.pk} ({old_instance.inventory} → 0)")
        _send_zero_inventory_sms(instance)
        cache.set(cache_key, True, timeout=60)  # قفل 60 ثانیه

    except Room.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error in room_manual_inventory_zero_sms: {e}", exc_info=True)


# ===================================================================
# 3. تابع مشترک برای ارسال SMS (جلوگیری از تکرار کد)
# ===================================================================
def _send_zero_inventory_sms(room):
    """ارسال SMS وقتی موجودی صفر شد (رزرو یا دستی)"""
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
# 6. مدیریت پرداخت، امتیاز، تخفیف، کیف پول
# ===================================================================
@receiver(post_save, sender=Reservationhotel)
def notify_status_change_and_assign_points(sender, instance, created, **kwargs):
    if get_skip_points_and_sms():
        return

    channel_layer = get_channel_layer()
    cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
    cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
    cache_key_points = f"points_assignment_lock_{instance.tracking_code}"
    cache_key_discount = f"discount_processing_lock_{instance.tracking_code}"

    # --- رد رزرو ---
    if instance.capacity_status == 'rejected':
        with transaction.atomic():
            for r in ReservationRoom.objects.filter(reservation=instance).select_related('room'):
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                is_auto_approved = instance.capacity_status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
        cache.delete_many([cache_key_approval, cache_key_payment])

    # --- پرداخت موفق ---
    elif instance.payment_status == 'paid':
        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)

            # تخصیص امتیاز
            if not reservation.points_assigned:
                cache.set(cache_key_points, True, timeout=60)
                total_points = sum(
                    (rr.room.customer_club_points or 0) * rr.quantity
                    for rr in reservation.reservation_rooms.select_related('room').all()
                )
                if total_points > 0:
                    points_obj, _ = CustomerClubPoint.objects.get_or_create(user=reservation.buyer, defaults={'points': 0})
                    points_obj.points += total_points
                    set_skip_points_and_sms(True)
                    points_obj.save()
                    set_skip_points_and_sms(False)
                    send_customer_club_add_sms(
                        phone_number=reservation.buyer.phone_number,
                        user_name=reservation.buyer.first_name or reservation.buyer.phone_number,
                        added_points=total_points,
                        current_points=points_obj.points
                    )
                reservation.points_assigned = True
                reservation.save(update_fields=['points_assigned'])
                cache.delete(cache_key_points)

            # پردازش کد تخفیف
            if reservation.applied_discount_code and not reservation.discount_processed:
                code = reservation.applied_discount_code.upper()
                discount_obj = None
                discount_type = None
                try:
                    discount_obj = RoomDiscountCode.objects.select_for_update().get(code__iexact=code)
                    discount_type = 'room'
                except RoomDiscountCode.DoesNotExist:
                    try:
                        discount_obj = HotelDiscountCode.objects.select_for_update().get(code__iexact=code)
                        discount_type = 'hotel'
                    except HotelDiscountCode.DoesNotExist:
                        return

                if reservation.buyer not in discount_obj.activated_users.all():
                    try:
                        discount_obj.apply_discount(reservation.buyer)
                    except ValueError as e:
                        logger.error(f"Discount apply error: {e}")
                        return

                activation_filter = {
                    'user': reservation.buyer,
                    'discount_type': discount_type,
                    **({'room_discount_code': discount_obj} if discount_type == 'room' else {'hotel_discount_code': discount_obj}),
                }
                record = DiscountActivationRecord.objects.select_for_update().filter(**activation_filter).first()
                if record and not record.reward_claimed:
                    record.reward_claimed = True
                    record.save(update_fields=['reward_claimed'])

                reservation.discount_processed = True
                reservation.save(update_fields=['discount_processed'])

        # برداشت از کیف پول
        if instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
            with transaction.atomic():
                try:
                    wallet = Wallet.objects.select_for_update().get(user=instance.buyer)
                    if wallet.balance >= instance.wallet_withdrawal_amount:
                        wallet.balance -= instance.wallet_withdrawal_amount
                        wallet.save()
                        instance.wallet_withdrawn = True
                        instance.save(update_fields=['wallet_withdrawn'])
                except Wallet.DoesNotExist:
                    pass

    # ارسال وضعیت از طریق WebSocket
    async_to_sync(channel_layer.group_send)(
        f"reservation_{instance.tracking_code}",
        {
            "type": "status_update",
            "message": {"capacity_status": instance.capacity_status},
        },
    )


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