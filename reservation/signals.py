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
from .models import (
    Reservationhotel, ReservationRoom, ReservationRoomPassenger,
    RoomDiscountCode, HotelDiscountCode, DiscountActivationRecord,
    Passenger, RoomDatePrice, Room
)

# تنظیم لاگینگ برای دیباگ
logger = logging.getLogger(__name__)

# سیگنال برای به‌روزرسانی موجودی اتاق هنگام ذخیره رزرو اتاق
@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    """
    به‌روزرسانی موجودی اتاق هنگام ذخیره یا ویرایش رزرو اتاق.
    """
    room = instance.room
    total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
    room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
    room.save(update_fields=['inventory'])
    logger.debug(f"Updated inventory for room {room.id}: {room.inventory}")

# سیگنال برای به‌روزرسانی موجودی اتاق هنگام حذف رزرو اتاق
@receiver(post_delete, sender=ReservationRoom)
def update_room_inventory_on_delete(sender, instance, **kwargs):
    """
    به‌روزرسانی موجودی اتاق هنگام حذف رزرو اتاق.
    """
    room = instance.room
    total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
    room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
    room.save(update_fields=['inventory'])
    logger.debug(f"Updated inventory for room {room.id} after deletion: {room.inventory}")

# سیگنال برای افزودن مسافر به دفترچه مسافران
@receiver(post_save, sender=ReservationRoomPassenger)
def add_to_passenger_book(sender, instance, created, **kwargs):
    """
    وقتی یک مسافر جدید در ReservationRoomPassenger ذخیره می‌شود،
    او را به دفترچه مسافران کاربر (Passenger) اضافه می‌کنیم.
    - مسافر اصلی باید تمام فیلدها (national_code و mobile_number) را داشته باشد.
    - سایر مسافران حتی بدون national_code یا mobile_number ثبت می‌شوند.
    """
    if not created:
        logger.debug(f"Skipping update for ReservationRoomPassenger {instance.id} (not created)")
        return

    try:
        user = instance.reservation_room.reservation.buyer
        if not user:
            logger.error(f"No buyer found for reservation {instance.reservation_room.reservation.id}")
            return
    except AttributeError as e:
        logger.error(f"Error accessing user for ReservationRoomPassenger {instance.id}: {e}")
        return

    phone_number = instance.mobile_number
    identification_code = instance.national_code

    if instance.passenger_type == 'primary':
        if not identification_code:
            logger.error(f"Primary passenger {instance.id} missing national_code")
            return
        if not phone_number or not re.match(r'^09\d{9}$', phone_number):
            logger.error(f"Primary passenger {instance.id} missing or invalid mobile_number: {phone_number}")
            return
    else:
        if not phone_number or not re.match(r'^09\d{9}$', phone_number):
            phone_number = '09123456789'
            logger.warning(f"Invalid or missing phone_number for ReservationRoomPassenger {instance.id}. Using default: {phone_number}")
        if not identification_code:
            identification_code = f"{instance.first_name}_{instance.last_name}_temp".replace(" ", "_")[:10]
            logger.warning(f"Missing national_code for ReservationRoomPassenger {instance.id}. Using temp ID: {identification_code}")

    try:
        passenger_exists = Passenger.objects.filter(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            identification_code=identification_code
        ).exists()

        if passenger_exists:
            logger.debug(f"Passenger with identification_code {identification_code} already exists for user {user.id}")
            return

        passenger = Passenger.objects.create(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            phone_number=phone_number,
            identification_code=identification_code
        )
        logger.info(f"Passenger created for user {user.id} with identification_code {identification_code} (Passenger ID: {passenger.id})")
    except ValidationError as e:
        logger.error(f"Validation error creating Passenger for {instance.first_name} {instance.last_name}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating Passenger for {instance.first_name} {instance.last_name}: {e}")

# سیگنال برای به‌روزرسانی وضعیت هتل هنگام تغییر بازه‌های قیمتی
@receiver([post_save, post_delete], sender=RoomDatePrice)
def update_hotel_status(sender, instance, **kwargs):
    """
    پس از ذخیره یا حذف بازه زمانی، وضعیت تیک‌های هتل را به‌روزرسانی می‌کند.
    """
    hotel = instance.room.hotel
    if hotel:
        if not hotel.has_active_date_prices():
            hotel.is_special_offer = False
            hotel.is_flash_sale = False
            hotel.is_best_seller = False
            hotel.save(update_fields=['is_special_offer', 'is_flash_sale', 'is_best_seller'])
            logger.debug(f"Updated hotel {hotel.id} status: is_special_offer={hotel.is_special_offer}, is_flash_sale={hotel.is_flash_sale}, is_best_seller={hotel.is_best_seller}")

# سیگنال برای مدیریت کد تخفیف و به‌روزرسانی وضعیت رزرو
@receiver(post_save, sender=Reservationhotel)
def notify_status_change_and_handle_discount(sender, instance, created, **kwargs):
    """
    مدیریت کد تخفیف هنگام تغییر وضعیت رزرو به 'paid' و ارسال به‌روزرسانی وضعیت.
    """
    channel_layer = get_channel_layer()
    cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
    cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
    timer = None

    # مدیریت کد تخفیف هنگام تغییر وضعیت به paid
    if not created and instance.status == 'paid' and instance.applied_discount_code:
        with transaction.atomic():
            try:
                # پیدا کردن کد تخفیف
                room_discount = None
                hotel_discount = None
                try:
                    room_discount = RoomDiscountCode.objects.select_for_update().get(code=instance.applied_discount_code)
                except RoomDiscountCode.DoesNotExist:
                    try:
                        hotel_discount = HotelDiscountCode.objects.select_for_update().get(code=instance.applied_discount_code)
                    except HotelDiscountCode.DoesNotExist:
                        logger.error(f"کد تخفیف {instance.applied_discount_code} برای رزرو {instance.tracking_code} یافت نشد.")
                        return

                discount_obj = room_discount or hotel_discount

                # بررسی تعداد استفاده باقی‌مانده
                if discount_obj.remaining_uses <= 0:
                    logger.error(f"کد تخفیف {instance.applied_discount_code} دیگر قابل استفاده نیست.")
                    return

                # بررسی اینکه کاربر قبلاً از کد استفاده نکرده باشد
                activation_exists = DiscountActivationRecord.objects.filter(
                    user=instance.buyer,
                    **{'room_discount_code': room_discount} if room_discount else {'hotel_discount_code': hotel_discount},
                    reward_claimed=True
                ).exists()

                if activation_exists:
                    logger.error(f"کاربر {instance.buyer} قبلاً از کد تخفیف {instance.applied_discount_code} استفاده کرده است.")
                    return

                # بررسی اعتبار کد تخفیف هتل برای اتاق‌ها
                if hotel_discount:
                    rooms = instance.reservation_rooms.all()
                    if not all(room.room.hotel == hotel_discount.hotel for room in rooms):
                        logger.error(f"کد تخفیف هتل {instance.applied_discount_code} برای اتاق‌های این رزرو معتبر نیست.")
                        return

                # اعمال کد تخفیف و کاهش remaining_uses
                discount_obj.remaining_uses -= 1
                discount_obj.activated_users.add(instance.buyer)
                discount_obj.save()

                # ثبت در DiscountActivationRecord با reward_claimed=True
                activation_record = DiscountActivationRecord.objects.create(
                    user=instance.buyer,
                    discount_type='room' if room_discount else 'hotel',
                    room_discount_code=room_discount,
                    hotel_discount_code=hotel_discount,
                    reward_claimed=True
                )

                logger.info(f"کد تخفیف {instance.applied_discount_code} برای رزرو {instance.tracking_code} با موفقیت ثبت شد. remaining_uses: {discount_obj.remaining_uses}, reward_claimed: {activation_record.reward_claimed}")

            except Exception as e:
                logger.error(f"خطا در ثبت کد تخفیف برای رزرو {instance.tracking_code}: {str(e)}")
                raise  # برای لغو تراکنش در صورت خطا

    # مدیریت وضعیت‌های دیگر
    if instance.status == "cancelled":
        rooms = ReservationRoom.objects.filter(reservation=instance).select_related('room')
        with transaction.atomic():
            for r in rooms:
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                is_auto_approved = instance.status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
        cache.delete_many([cache_key_approval, cache_key_payment])
        timer = 0

    elif instance.status in ["paid", "unconfirmed"]:
        cache.delete_many([cache_key_approval, cache_key_payment])

    async_to_sync(channel_layer.group_send)(
        f"reservation_{instance.tracking_code}",
        {
            "type": "status_update",
            "message": {
                "status": instance.status,
                "timer": timer,
            },
        },
    )