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
            room_name = room.title.strip() if room.title else "اتاق"
            room_full_name = f"{room_name} - آیدی {room.pk}"[:20]
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
        room = Room.objects.select_for_update().get(pk=room.pk)
        total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
        previous_inventory = room.inventory
        room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
        room.save(update_fields=['inventory'])
        logger.debug(f"Updated inventory for room {room.id} after deletion: {room.inventory}")

        if room.inventory == 0 and previous_inventory != 0:
            room_name = room.title.strip() if room.title else "اتاق"
            room_full_name = f"{room_name} - آیدی {room.pk}"[:20]
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
def notify_status_change_and_assign_points(sender, instance, created, **kwargs):
    """
    مدیریت کد تخفیف، امتیازهای باشگاه مشتریان، برداشت از کیف پول و ارسال به‌روزرسانی وضعیت از طریق WebSocket.
    
    وظایف:
    1. اگر payment_status به 'paid' تغییر کند:
       - تخصیص امتیازهای باشگاه مشتریان و ارسال SMS افزایش امتیاز بلافاصله.
       - اگر کد تخفیف اعمال شده باشد، reward_claimed=True تنظیم می‌شود و کاربر به activated_users اضافه می‌شود.
       - کاهش remaining_uses در مدل کد تخفیف.
    2. اگر wallet_withdrawal_amount > 0 باشد، مبلغ از کیف پول کسر می‌شود.
    3. هنگام تغییر capacity_status به 'rejected'، موجودی اتاق‌ها بازگردانده می‌شود، اما رکورد DiscountActivationRecord حفظ می‌شود.
    4. ارسال اعلان به‌روزرسانی وضعیت رزرو از طریق WebSocket.
    """
    if get_skip_points_and_sms():
        logger.info(f"اجرای سیگنال برای رزرو {instance.tracking_code} نادیده گرفته شد به دلیل get_skip_points_and_sms=True.")
        return

    channel_layer = get_channel_layer()
    cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
    cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
    cache_key_points = f"points_assignment_lock_{instance.tracking_code}"
    cache_key_discount = f"discount_processing_lock_{instance.tracking_code}"
    timer = None

    logger.debug(f"سیگنال برای رزرو {instance.tracking_code} اجرا شد. payment_status={instance.payment_status}, discount_processed={instance.discount_processed}, applied_discount_code={instance.applied_discount_code}")

    # بررسی قفل برای جلوگیری از پردازش چندباره (موقتاً غیرفعال برای تست)
    # if cache.get(cache_key_points) or cache.get(cache_key_discount):
    #     logger.info(f"Processing skipped for {instance.tracking_code} due to lock")
    #     return

    # بررسی وضعیت لغو رزرو
    if instance.capacity_status == 'rejected':
        rooms = ReservationRoom.objects.filter(reservation=instance).select_related('room')
        with transaction.atomic():
            for r in rooms:
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                is_auto_approved = instance.capacity_status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
                logger.debug(f"Inventory reverted for room {room.id}: quantity={r.quantity}, is_auto_approved={is_auto_approved}")

            # رکورد DiscountActivationRecord برای کد تخفیف در زمان لغو رزرو حفظ می‌شود
            if instance.applied_discount_code and instance.payment_status != 'paid':
                logger.debug(f"کد تخفیف {instance.applied_discount_code} برای رزرو لغوشده {instance.tracking_code} پردازش نمی‌شود (پرداخت نشده).")

        cache.delete_many([cache_key_approval, cache_key_payment])
        timer = 0
        logger.debug(f"رزرو {instance.tracking_code} رد شد، تایمرها حذف شدند.")

    # بررسی تغییر وضعیت به پرداخت‌شده و تخصیص امتیازها و مدیریت کد تخفیف
    elif instance.payment_status == 'paid':
        logger.info(f"وضعیت پرداخت برای رزرو {instance.tracking_code} به 'paid' تغییر کرد. بررسی تخصیص امتیاز و کد تخفیف...")
        with transaction.atomic():
            # قفل کردن رکورد رزرو برای جلوگیری از race condition
            reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)

            # پردازش امتیازها (اگر قبلاً انجام نشده)
            if not reservation.points_assigned:
                cache.set(cache_key_points, True, timeout=60)
                total_points = 0
                for res_room in reservation.reservation_rooms.select_related('room').all():
                    room = res_room.room
                    quantity = res_room.quantity
                    points = room.customer_club_points or 0
                    total_points += points * quantity

                if total_points > 0:
                    customer_points, created = CustomerClubPoint.objects.get_or_create(
                        user=reservation.buyer,
                        defaults={'points': 0}
                    )
                    customer_points.points += total_points
                    set_skip_points_and_sms(True)
                    customer_points.save()
                    set_skip_points_and_sms(False)
                    logger.info(f"امتیازهای باشگاه مشتریان ({total_points}) به کاربر {reservation.buyer.phone_number} برای رزرو {reservation.tracking_code} اضافه شد.")

                    # ارسال SMS افزایش امتیاز بلافاصله
                    send_customer_club_add_sms(
                        phone_number=reservation.buyer.phone_number,
                        user_name=reservation.buyer.first_name or reservation.buyer.phone_number,
                        added_points=total_points,
                        current_points=customer_points.points
                    )
                else:
                    logger.info(f"هیچ امتیازی برای رزرو {reservation.tracking_code} تخصیص داده نشد (total_points=0).")

                # علامت‌گذاری رزرو به‌عنوان تخصیص‌شده
                reservation.points_assigned = True
                reservation.save(update_fields=['points_assigned'])
                cache.delete(cache_key_points)

            # پردازش کد تخفیف (اگر اعمال شده و قبلاً پردازش نشده)
            if reservation.applied_discount_code and not reservation.discount_processed:
                logger.info(f"شروع پردازش کد تخفیف {reservation.applied_discount_code} برای رزرو {reservation.tracking_code}")
                code = reservation.applied_discount_code.upper()
                discount_obj = None
                discount_type = None

                # بررسی وجود کد تخفیف
                try:
                    discount_obj = RoomDiscountCode.objects.select_for_update().get(code__iexact=code)
                    discount_type = 'room'
                    logger.debug(f"RoomDiscountCode پیدا شد: code={discount_obj.code}, remaining_uses={discount_obj.remaining_uses}")
                except RoomDiscountCode.DoesNotExist:
                    try:
                        discount_obj = HotelDiscountCode.objects.select_for_update().get(code__iexact=code)
                        discount_type = 'hotel'
                        logger.debug(f"HotelDiscountCode پیدا شد: code={discount_obj.code}, remaining_uses={discount_obj.remaining_uses}")
                    except HotelDiscountCode.DoesNotExist:
                        logger.error(f"کد تخفیف {code} برای رزرو {reservation.tracking_code} یافت نشد.")
                        return

                # اعمال کد تخفیف با استفاده از متد apply_discount
                if discount_obj:
                    logger.debug(f"بررسی کاربر {reservation.buyer.phone_number} در activated_users: {reservation.buyer in discount_obj.activated_users.all()}")
                    if reservation.buyer not in discount_obj.activated_users.all():
                        try:
                            discount_obj.apply_discount(reservation.buyer)
                            logger.info(f"کاربر {reservation.buyer.phone_number} با موفقیت به activated_users کد تخفیف {code} اضافه شد. remaining_uses={discount_obj.remaining_uses}")
                        except ValueError as e:
                            logger.error(f"خطا در اعمال کد تخفیف {code} برای کاربر {reservation.buyer.phone_number}: {str(e)}")
                            return
                    else:
                        logger.warning(f"کاربر {reservation.buyer.phone_number} قبلاً در activated_users کد {code} وجود دارد.")

                    # به‌روزرسانی reward_claimed
                    activation_filter = {
                        'user': reservation.buyer,
                        'discount_type': discount_type,
                        **({'room_discount_code': discount_obj} if discount_type == 'room' else {'hotel_discount_code': discount_obj}),
                    }
                    activation_record = DiscountActivationRecord.objects.select_for_update().filter(**activation_filter).first()
                    if activation_record and not activation_record.reward_claimed:
                        activation_record.reward_claimed = True
                        activation_record.save(update_fields=['reward_claimed'])
                        logger.info(f"reward_claimed برای رکورد {activation_record.id} به True تنظیم شد.")
                    elif activation_record:
                        logger.debug(f"رکورد فعال‌سازی {activation_record.id} قبلاً reward_claimed=True بوده است.")

                    reservation.discount_processed = True
                    reservation.save(update_fields=['discount_processed'])
                    logger.info(f"پردازش کد تخفیف برای رزرو {reservation.tracking_code} تکمیل شد.")

    # بررسی برداشت از کیف پول هنگام پرداخت نهایی
    if instance.payment_status == 'paid' and instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
        logger.info(f"برداشت از کیف پول برای رزرو {instance.tracking_code} در حال انجام است...")
        with transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(user=instance.buyer)
                if wallet.balance < instance.wallet_withdrawal_amount:
                    logger.error(f"موجودی کیف پول برای رزرو {instance.tracking_code} کافی نیست. برداشت لغو شد.")
                    return

                wallet.balance -= instance.wallet_withdrawal_amount
                wallet.save()
                instance.wallet_withdrawn = True
                instance.save(update_fields=['wallet_withdrawn'])
                logger.info(f"مبلغ {instance.wallet_withdrawal_amount} از کیف پول کاربر {instance.buyer.phone_number} برای رزرو {instance.tracking_code} کسر شد.")
            except Wallet.DoesNotExist:
                logger.error(f"کیف پول برای کاربر {instance.buyer.phone_number} یافت نشد.")
                return
            except Exception as e:
                logger.error(f"خطا در برداشت از کیف پول برای رزرو {instance.tracking_code}: {str(e)}")
                raise

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
    
    
    @receiver(post_save, sender=UserCancellation)
    def update_reservation_on_cancellation(sender, instance, **kwargs):
            if instance.status == 'approved':
                reservation = instance.reservation
                reservation.capacity_status = 'rejected'  # وضعیت رزرو لغو شد
                reservation.payment_status = 'unpaid'    # وضعیت پرداخت لغو شد
                reservation.save()