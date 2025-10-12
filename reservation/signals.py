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
from reservation.sms.sms import send_room_availability_sms

# تنظیم لاگینگ برای دیباگ
logger = logging.getLogger(__name__)

@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    """
    به‌روزرسانی موجودی اتاق هنگام ذخیره یا ویرایش رزرو اتاق و ارسال پیامک در صورت صفر شدن موجودی.
    """
    room = instance.room
    with transaction.atomic():
        # قفل کردن رکورد برای جلوگیری از race condition
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])
        logger.debug(f"Updated inventory for room {room.id}: {room.inventory}")

        # بررسی و ارسال پیامک در صورت صفر شدن موجودی
        if room.inventory == 0 and previous_inventory != 0:
            room_name = room.title.strip() if room.title else "اتاق"
            room_full_name = f"{room_name} - آیدی {room.pk}"[:20]  # محدود به 20 کاراکتر
            status = "تکمیل"
            hotel_name = room.hotel.name if room.hotel and hasattr(room.hotel, 'name') else None

            logger.info(f"Room {room.pk}: Inventory is 0, sending SMS for '{room_full_name}'")
            try:
                success = send_room_availability_sms(
                    room_name=room_full_name,
                    status=status,
                    hotel_name=hotel_name,
                    pattern_section='roomavailability'
                )
                if success:
                    logger.info(f"Room {room.pk}: SMS sent successfully for '{room_full_name}'")
                else:
                    logger.error(f"Room {room.pk}: Failed to send SMS for '{room_full_name}'")
            except Exception as e:
                logger.error(f"Room {room.pk}: Exception while sending SMS for '{room_full_name}': {str(e)}")

@receiver(post_delete, sender=ReservationRoom)
def update_room_inventory_on_delete(sender, instance, **kwargs):
    """
    به‌روزرسانی موجودی اتاق هنگام حذف رزرو اتاق و ارسال پیامک در صورت صفر شدن موجودی.
    """
    room = instance.room
    with transaction.atomic():
        # قفل کردن رکورد برای جلوگیری از race condition
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])
        logger.debug(f"Updated inventory for room {room.id} after deletion: {room.inventory}")

        # بررسی و ارسال پیامک در صورت صفر شدن موجودی
        if room.inventory == 0 and previous_inventory != 0:
            room_name = room.title.strip() if room.title else "اتاق"
            room_full_name = f"{room_name} - آیدی {room.pk}"[:20]  # محدود به 20 کاراکتر
            status = "تکمیل"
            hotel_name = room.hotel.name if room.hotel and hasattr(room.hotel, 'name') else None

            logger.info(f"Room {room.pk}: Inventory is 0, sending SMS for '{room_full_name}'")
            try:
                success = send_room_availability_sms(
                    room_name=room_full_name,
                    status=status,
                    hotel_name=hotel_name,
                    pattern_section='roomavailability'
                )
                if success:
                    logger.info(f"Room {room.pk}: SMS sent successfully for '{room_full_name}'")
                else:
                    logger.error(f"Room {room.pk}: Failed to send SMS for '{room_full_name}'")
            except Exception as e:
                logger.error(f"Room {room.pk}: Exception while sending SMS for '{room_full_name}': {str(e)}")

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

@receiver(post_save, sender=Reservationhotel)
def notify_status_change_and_handle_discount(sender, instance, created, **kwargs):
    """
    مدیریت کد تخفیف هنگام تغییر وضعیت رزرو به 'paid' و ارسال به‌روزرسانی وضعیت از طریق WebSocket.
    
    وظایف:
    1. اگر payment_status به 'paid' تغییر کند و کد تخفیف اعمال شده باشد، یک رکورد
       DiscountActivationRecord با reward_claimed=True ایجاد یا به‌روزرسانی می‌شود.
    2. هنگام تغییر capacity_status به 'rejected'، موجودی اتاق‌ها بازگردانده می‌شود.
    3. ارسال اعلان به‌روزرسانی وضعیت رزرو از طریق WebSocket.
    """
    channel_layer = get_channel_layer()
    cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
    cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
    timer = None

    logger.debug(f"سیگنال post_save برای رزرو {instance.tracking_code} فراخوانی شد. "
                 f"payment_status: {instance.payment_status}, "
                 f"capacity_status: {instance.capacity_status}, "
                 f"applied_discount_code: {instance.applied_discount_code}, "
                 f"created: {created}")

    # مدیریت کد تخفیف هنگام تغییر وضعیت به paid
    if not created and instance.payment_status == 'paid' and instance.applied_discount_code:
        with transaction.atomic():
            try:
                logger.debug(f"شروع اعمال کد تخفیف برای رزرو {instance.tracking_code}")

                # پیدا کردن کد تخفیف با case-insensitive
                room_discount = None
                hotel_discount = None
                try:
                    room_discount = RoomDiscountCode.objects.select_for_update().get(code__iexact=instance.applied_discount_code)
                    logger.debug(f"RoomDiscountCode پیدا شد: {room_discount.code}")
                except RoomDiscountCode.DoesNotExist:
                    logger.debug("RoomDiscountCode پیدا نشد، جستجو برای HotelDiscountCode")
                    try:
                        hotel_discount = HotelDiscountCode.objects.select_for_update().get(code__iexact=instance.applied_discount_code)
                        logger.debug(f"HotelDiscountCode پیدا شد: {hotel_discount.code}")
                    except HotelDiscountCode.DoesNotExist:
                        logger.error(f"کد تخفیف {instance.applied_discount_code} برای رزرو {instance.tracking_code} یافت نشد.")
                        return

                discount_obj = room_discount or hotel_discount

                # بررسی اعتبار کد تخفیف برای اتاق‌ها یا هتل
                if hotel_discount:
                    rooms = instance.reservation_rooms.all()
                    if not rooms.exists():
                        logger.error(f"هیچ اتاقی برای رزرو {instance.tracking_code} یافت نشد.")
                        return
                    if not all(rr.room.hotel == hotel_discount.hotel for rr in rooms):
                        logger.error(f"کد تخفیف هتل {instance.applied_discount_code} برای اتاق‌های این رزرو معتبر نیست.")
                        return
                elif room_discount:
                    if not any(rr.room == room_discount.room for rr in instance.reservation_rooms.all()):
                        logger.error(f"کد تخفیف اتاق {instance.applied_discount_code} برای اتاق‌های این رزرو معتبر نیست.")
                        return

                # بررسی تعداد استفاده باقی‌مانده
                if discount_obj.remaining_uses <= 0:
                    logger.error(f"کد تخفیف {instance.applied_discount_code} دیگر قابل استفاده نیست. remaining_uses: {discount_obj.remaining_uses}")
                    return

                # بررسی اینکه کاربر قبلاً از کد استفاده نکرده باشد
                activation_exists = DiscountActivationRecord.objects.filter(
                    user=instance.buyer,
                    discount_type='room' if room_discount else 'hotel',
                    reward_claimed=True,
                    **({'room_discount_code': room_discount} if room_discount else {'hotel_discount_code': hotel_discount})
                ).exists()
                if activation_exists:
                    logger.error(f"کاربر {instance.buyer} قبلاً از کد تخفیف {instance.applied_discount_code} استفاده کرده است.")
                    return

                # کاهش تعداد استفاده‌های باقی‌مانده و افزودن کاربر به activated_users
                discount_obj.remaining_uses -= 1
                discount_obj.activated_users.add(instance.buyer)
                discount_obj.save(update_fields=['remaining_uses'])
                logger.debug(f"remaining_uses به‌روزرسانی شد: {discount_obj.remaining_uses}")

                # ثبت یا به‌روزرسانی DiscountActivationRecord با reward_claimed=True
                activation_record, created = DiscountActivationRecord.objects.get_or_create(
                    user=instance.buyer,
                    discount_type='room' if room_discount else 'hotel',
                    **({'room_discount_code': room_discount} if room_discount else {'hotel_discount_code': hotel_discount}),
                    defaults={'reward_claimed': True}
                )
                if not created and not activation_record.reward_claimed:
                    activation_record.reward_claimed = True
                    activation_record.save(update_fields=['reward_claimed'])
                logger.debug(f"DiscountActivationRecord {'ایجاد شد' if created else 'به‌روزرسانی شد'} با reward_claimed=True: ID {activation_record.id}")

                logger.info(f"کد تخفیف {instance.applied_discount_code} برای رزرو {instance.tracking_code} با موفقیت ثبت شد.")

            except Exception as e:
                logger.error(f"خطا در ثبت کد تخفیف برای رزرو {instance.tracking_code}: {str(e)}")
                raise  # برای rollback تراکنش

    # بررسی وضعیت لغو رزرو
    if instance.capacity_status == 'rejected':
        rooms = instance.reservation_rooms.all().select_related('room')
        with transaction.atomic():
            for r in rooms:
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                # فرض می‌کنیم متد revert_inventory_for_cancellation در مدل Room تعریف شده است
                is_auto_approved = instance.capacity_status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
                logger.debug(f"Inventory reverted for room {room.id}: quantity={r.quantity}, is_auto_approved={is_auto_approved}")
        cache.delete_many([cache_key_approval, cache_key_payment])
        timer = 0
        logger.debug(f"رزرو {instance.tracking_code} رد شد، تایمرها حذف شدند.")

    # حذف تایمرها در صورت تأیید یا رد ظرفیت
    elif instance.capacity_status in ['confirmed', 'rejected']:
        cache.delete_many([cache_key_approval, cache_key_payment])
        logger.debug(f"تایمرها برای رزرو {instance.tracking_code} حذف شدند.")

    # ارسال اعلان به‌روزرسانی وضعیت فقط برای capacity_status
    async_to_sync(channel_layer.group_send)(
        f"reservation_{instance.tracking_code}",
        {
            "type": "status_update",
            "message": {
                "capacity_status": instance.capacity_status,
                "timer": timer,
            },
        },
    )
    logger.debug(f"اعلان به‌روزرسانی وضعیت برای رزرو {instance.tracking_code} ارسال شد.")