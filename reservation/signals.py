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
    Passenger, RoomDatePrice, Room, Wallet
)
from reservation.sms.sms import send_room_availability_sms
from customer_club.models import CustomerClubPoint
from customer_club.sms.sms import send_customer_club_add_sms, send_customer_club_deduct_sms
from threading import Timer
import jdatetime

logger = logging.getLogger(__name__)

# تابع برای ارسال SMS کسر با تاخیر 2 دقیقه
def delayed_send_deduct_sms(phone_number, user_name, deducted_points, current_points):
    send_customer_club_deduct_sms(
        phone_number=phone_number,
        user_name=user_name,
        deducted_points=deducted_points,
        current_points=current_points
    )

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
       - اگر کد تخفیف اعمال شده باشد، reward_claimed=True تنظیم می‌شود.
       - کاهش remaining_uses و افزودن کاربر به activated_users.
       - امتیاز در ActivateDiscountCodeView کسر شده، پس اینجا کسر نمی‌شود.
    2. اگر wallet_withdrawal_amount > 0 باشد، مبلغ از کیف پول کسر می‌شود.
    3. هنگام تغییر capacity_status به 'rejected'، موجودی اتاق‌ها بازگردانده می‌شود، اما رکورد DiscountActivationRecord حفظ می‌شود.
    4. ارسال اعلان به‌روزرسانی وضعیت رزرو از طریق WebSocket.
    """
    if get_skip_points_and_sms():
        logger.info(f"اجرای سیگنال برای رزرو {instance.tracking_code} نادیده گرفته شد.")
        return

    channel_layer = get_channel_layer()
    cache_key_approval = f"reservation_approval_timer_{instance.tracking_code}"
    cache_key_payment = f"reservation_payment_timer_{instance.tracking_code}"
    cache_key_points = f"points_assignment_lock_{instance.tracking_code}"
    timer = None

    # بررسی قفل برای جلوگیری از تخصیص چندباره امتیاز
    if cache.get(cache_key_points):
        logger.info(f"Points assignment skipped for {instance.tracking_code} due to lock")
        return

    # بررسی وضعیت لغو رزرو
    if instance.capacity_status == 'rejected':
        rooms = ReservationRoom.objects.filter(reservation=instance).select_related('room')
        with transaction.atomic():
            for r in rooms:
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                is_auto_approved = instance.capacity_status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
                logger.debug(f"Inventory reverted for room {room.id}: quantity={r.quantity}, is_auto_approved={is_auto_approved}")

            # رکورد DiscountActivationRecord حذف نمی‌شود تا کد تخفیف در لیست جوایز باقی بماند
            if instance.applied_discount_code:
                logger.debug(f"رکورد DiscountActivationRecord برای کد تخفیف {instance.applied_discount_code} در زمان لغو رزرو حفظ می‌شود.")

        cache.delete_many([cache_key_approval, cache_key_payment])
        timer = 0
        logger.debug(f"رزرو {instance.tracking_code} رد شد، تایمرها حذف شدند.")

    # بررسی تغییر وضعیت به پرداخت‌شده و تخصیص امتیازها و مدیریت کد تخفیف
    elif instance.payment_status == 'paid' and not instance.points_assigned:
        logger.info(f"وضعیت پرداخت برای رزرو {instance.tracking_code} به 'paid' تغییر کرد. بررسی تخصیص امتیاز و کد تخفیف...")
        with transaction.atomic():
            # قفل کردن رکورد رزرو برای جلوگیری از race condition
            reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
            if reservation.points_assigned:
                logger.info(f"Points already assigned for {reservation.tracking_code}, skipping.")
                return

            # تنظیم قفل کش
            cache.set(cache_key_points, True, timeout=60)

            # محاسبه مجموع امتیازهای اتاق‌ها
            total_points = 0
            for res_room in reservation.reservation_rooms.select_related('room').all():
                room = res_room.room
                quantity = res_room.quantity
                points = room.customer_club_points or 0
                total_points += points * quantity

            # به‌روزرسانی یا ایجاد CustomerClubPoint برای کاربر
            customer_points, created = CustomerClubPoint.objects.get_or_create(
                user=reservation.buyer,
                defaults={'points': 0}
            )
            if total_points > 0:
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

            # مدیریت کد تخفیف
            if reservation.applied_discount_code:
                logger.debug(f"شروع اعمال کد تخفیف برای رزرو {reservation.tracking_code}")
                code = reservation.applied_discount_code.upper()
                discount_obj = None
                discount_type = None

                try:
                    discount_obj = RoomDiscountCode.objects.select_for_update().get(code__iexact=code)
                    discount_type = 'room'
                    logger.debug(f"RoomDiscountCode پیدا شد: {discount_obj.code}")
                except RoomDiscountCode.DoesNotExist:
                    try:
                        discount_obj = HotelDiscountCode.objects.select_for_update().get(code__iexact=code)
                        discount_type = 'hotel'
                        logger.debug(f"HotelDiscountCode پیدا شد: {discount_obj.code}")
                    except HotelDiscountCode.DoesNotExist:
                        logger.error(f"کد تخفیف {code} برای رزرو {reservation.tracking_code} یافت نشد.")
                        return

                # بررسی اعتبار کد تخفیف برای اتاق‌ها یا هتل
                if discount_type == 'hotel':
                    rooms = reservation.reservation_rooms.all()
                    if not rooms.exists():
                        logger.error(f"هیچ اتاقی برای رزرو {reservation.tracking_code} یافت نشد.")
                        return
                    if not all(rr.room.hotel == discount_obj.hotel for rr in rooms):
                        logger.error(f"کد تخفیف هتل {code} برای اتاق‌های این رزرو معتبر نیست.")
                        return
                elif discount_type == 'room':
                    if not any(rr.room == discount_obj.room for rr in reservation.reservation_rooms.all()):
                        logger.error(f"کد تخفیف اتاق {code} برای اتاق‌های این رزرو معتبر نیست.")
                        return

                # چک‌های اضافی
                now_j = jdatetime.datetime.now().date()
                if discount_obj.expires_at and discount_obj.expires_at < now_j:
                    logger.error(f"کد تخفیف {code} منقضی شده است.")
                    return
                if discount_obj.users.exists() and reservation.buyer not in discount_obj.users.all():
                    logger.error(f"این کد تخفیف برای کاربر {reservation.buyer.phone_number} در دسترس نیست.")
                    return
                user_level = getattr(getattr(reservation.buyer, 'natural_profile', None), 'level', None)
                if discount_obj.user_level and discount_obj.user_level != user_level:
                    logger.error(f"این کد تخفیف برای سطح کاربری کاربر {reservation.buyer.phone_number} فعال نیست.")
                    return
                if discount_obj.remaining_uses <= 0:
                    logger.error(f"کد تخفیف {code} دیگر قابل استفاده نیست. remaining_uses: {discount_obj.remaining_uses}")
                    return

                # بررسی وجود رکورد فعال‌سازی قبلی
                activation_filter = {
                    'user': reservation.buyer,
                    'discount_type': discount_type,
                    **({'room_discount_code': discount_obj} if discount_type == 'room' else {'hotel_discount_code': discount_obj}),
                }
                activation_record = DiscountActivationRecord.objects.select_for_update().filter(**activation_filter).first()

                if not activation_record:
                    logger.error(f"رکورد فعال‌سازی برای کد تخفیف {code} و کاربر {reservation.buyer.phone_number} یافت نشد.")
                    return
                if activation_record.reward_claimed:
                    logger.info(f"کد تخفیف {code} قبلاً برای کاربر {reservation.buyer.phone_number} استفاده شده است (reward_claimed=True).")
                    return

                # به‌روزرسانی DiscountActivationRecord به reward_claimed=True
                logger.info(f"به‌روزرسانی DiscountActivationRecord برای رزرو {reservation.tracking_code}, user={reservation.buyer.phone_number}, code={code}")
                activation_record.reward_claimed = True
                activation_record.save(update_fields=['reward_claimed'])
                logger.debug(f"DiscountActivationRecord به‌روزرسانی شد با reward_claimed=True: ID={activation_record.id}")

                # کاهش تعداد استفاده‌های باقی‌مانده و افزودن کاربر به activated_users
                if discount_obj.remaining_uses > 0:
                    discount_obj.remaining_uses -= 1
                    discount_obj.activated_users.add(reservation.buyer)
                    discount_obj.save(update_fields=['remaining_uses'])
                    logger.debug(f"remaining_uses به‌روزرسانی شد: {discount_obj.remaining_uses}")

            # حذف قفل کش
            cache.delete(cache_key_points)

    # بررسی برداشت از کیف پول هنگام پرداخت نهایی
    elif instance.payment_status == 'paid' and instance.wallet_withdrawal_amount > 0 and not instance.wallet_withdrawn:
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