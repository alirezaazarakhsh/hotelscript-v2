import logging
import re
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
from django.db import transaction
from threading import local
import jdatetime
import traceback

from authentication import models

from .models import (
    Reservationhotel, ReservationRoom, ReservationRoomPassenger,
    Passenger, RoomDatePrice, Room, UserCancellation, Wallet
)
from bashgah_moshtarian.models import (
    RoomDiscountCode, HotelDiscountCode, DiscountActivationRecord, CustomerClubPoint
)
from reservation.sms.sms import send_room_availability_sms
from bashgah_moshtarian.sms.sms import send_customer_club_add_sms
from bashgah_moshtarian.sms.sms import send_customer_club_sms

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
# 6. مدیریت پرداخت، امتیاز، تخفیف، کیف پول - نسخه نهایی و اصلاح شده
# ===================================================================
@receiver(post_save, sender=Reservationhotel)
def handle_reservation_payment_complete(sender, instance, **kwargs):
    """
    سیگنال پس از ذخیره رزرو برای مدیریت وضعیت پرداخت و اقدامات بعدی
    """
    logger.info(f"🔔 سیگنال handle_reservation_payment_complete فراخوانی شد برای رزرو {instance.tracking_code}")
    logger.info(f"   payment_status={instance.payment_status}, wallet_withdrawal_amount={instance.wallet_withdrawal_amount}, wallet_withdrawn={instance.wallet_withdrawn}")
    
    if get_skip_points_and_sms():
        logger.info(f"سیگنال برای رزرو {instance.tracking_code} به دلیل فلگ skip نادیده گرفته شد.")
        return

    channel_layer = get_channel_layer()

    if instance.payment_status == 'paid':
        logger.info(f"🔵 پردازش رزرو پرداخت شده: {instance.tracking_code}")

        with transaction.atomic():
            reservation_refreshed = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
            fields_to_update = []

            # برداشت از کیف پول
            if reservation_refreshed.wallet_withdrawal_amount > 0 and not reservation_refreshed.wallet_withdrawn:
                logger.info(f"تلاش برای برداشت کیف پول برای رزرو {reservation_refreshed.tracking_code}...")
                success = _process_wallet_withdrawal(reservation_refreshed)
                if success:
                    logger.info(f"✅ برداشت کیف پول برای رزرو {reservation_refreshed.tracking_code} موفق بود.")
                    reservation_refreshed.refresh_from_db()
                else:
                    logger.error(f"❌ برداشت کیف پول برای رزرو {reservation_refreshed.tracking_code} شکست خورد.")

            # مصرف کد تخفیف
            if reservation_refreshed.applied_discount_code and not reservation_refreshed.discount_processed:
                logger.info(f"تلاش برای پردازش کد تخفیف {reservation_refreshed.applied_discount_code} برای رزرو {reservation_refreshed.tracking_code}...")
                success = _process_discount_code_optimized(reservation_refreshed)
                if success:
                    logger.info(f"✅ کد تخفیف برای رزرو {reservation_refreshed.tracking_code} پردازش شد.")
                    reservation_refreshed.refresh_from_db()
                else:
                    logger.error(f"❌ خطا در پردازش کد تخفیف رزرو {reservation_refreshed.tracking_code}")

            # تخصیص امتیاز
            if not reservation_refreshed.points_assigned:
                logger.info(f"تلاش برای تخصیص امتیاز برای رزرو {reservation_refreshed.tracking_code}...")
                success = _assign_customer_points(reservation_refreshed)
                if success:
                    logger.info(f"✅ امتیاز برای رزرو {reservation_refreshed.tracking_code} تخصیص داده شد.")
                    reservation_refreshed.refresh_from_db()
                else:
                    logger.error(f"❌ خطا در تخصیص امتیاز برای رزرو {reservation_refreshed.tracking_code}.")

            # ذخیره نهایی اگر نیاز به آپدیت فیلدها بود
            if fields_to_update:
                reservation_refreshed._skip_price_calculation_on_save = True
                reservation_refreshed.save(update_fields=fields_to_update)
                del reservation_refreshed._skip_price_calculation_on_save
                logger.info(f"✅ ذخیره نهایی رزرو {reservation_refreshed.tracking_code} با فیلدهای {fields_to_update}")

    elif instance.capacity_status == 'rejected':
        _handle_rejected_reservation(instance)

    # ارسال آپدیت به WebSocket
    _send_websocket_update(channel_layer, instance)



def _assign_customer_points(reservation):
    """تخصیص امتیاز باشگاه مشتریان"""
    cache_key = f"points_assignment_lock_{reservation.tracking_code}"
    if cache.get(cache_key):
        logger.info(f"Assign points for {reservation.tracking_code} skipped due to lock.")
        return False

    try:
        with transaction.atomic():
            reservation_refreshed = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if reservation_refreshed.points_assigned:
                logger.info(f"Points already assigned for {reservation_refreshed.tracking_code}, skipping.")
                return True

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
                point_obj.save(update_fields=['points'])
                set_skip_points_and_sms(False)

                send_customer_club_add_sms(
                    phone_number=reservation_refreshed.buyer.phone_number,
                    user_name=reservation_refreshed.buyer.get_full_name() or reservation_refreshed.buyer.phone_number,
                    added_points=total_points,
                    current_points=point_obj.points
                )
                logger.info(f"امتیاز {total_points:,} به {reservation_refreshed.buyer.phone_number} برای رزرو {reservation.tracking_code} اضافه شد. موجودی جدید: {point_obj.points:,}")
            else:
                logger.info(f"هیچ امتیازی برای رزرو {reservation.tracking_code} تخصیص داده نشد (total_points=0).")

            reservation_refreshed.points_assigned = True
            reservation_refreshed._skip_price_calculation_on_save = True 
            reservation_refreshed.save(update_fields=['points_assigned'])
            del reservation_refreshed._skip_price_calculation_on_save
            logger.info(f"رزرو {reservation.tracking_code} به عنوان دارای امتیاز پردازش‌شده علامت‌گذاری شد.")
            return True

    except Exception as e:
        logger.error(f"🔴 خطا در تخصیص امتیاز برای رزرو {reservation.tracking_code}: {e}")
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")
        return False
    finally:
        cache.delete(cache_key)

def _process_discount_code_optimized(reservation):
    """پردازش بهینه کد تخفیف پس از پرداخت موفق"""
    cache_key = f"discount_process_lock_{reservation.tracking_code}"
    if cache.get(cache_key):
        logger.info(f"Discount processing for {reservation.tracking_code} skipped due to lock.")
        return False

    try:
        with transaction.atomic():
            reservation_refreshed = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
            if reservation_refreshed.discount_processed:
                logger.info(f"کد تخفیف برای رزرو {reservation_refreshed.tracking_code} قبلاً پردازش شده است.")
                return True

            cache.set(cache_key, True, timeout=60)

            logger.info(f"🔵 شروع پردازش کد تخفیف: {reservation_refreshed.applied_discount_code} برای رزرو {reservation_refreshed.tracking_code}")

            discount_obj = None
            discount_type = None
            
            try:
                discount_obj = RoomDiscountCode.objects.select_for_update().get(
                    code__iexact=reservation_refreshed.applied_discount_code
                )
                discount_type = 'room'
                logger.info(f"✅ RoomDiscountCode پیدا شد: {discount_obj.code}")
            except RoomDiscountCode.DoesNotExist:
                try:
                    discount_obj = HotelDiscountCode.objects.select_for_update().get(
                        code__iexact=reservation_refreshed.applied_discount_code
                    )
                    discount_type = 'hotel'
                    logger.info(f"✅ HotelDiscountCode پیدا شد: {discount_obj.code}")
                except HotelDiscountCode.DoesNotExist:
                    logger.error(f"❌ کد تخفیف {reservation_refreshed.applied_discount_code} برای رزرو {reservation_refreshed.tracking_code} یافت نشد.")
                    return False

            if discount_obj.expires_at and discount_obj.expires_at < jdatetime.datetime.now().date():
                logger.warning(f"❌ کد تخفیف {discount_obj.code} منقضی شده است.")
                return False

            if discount_obj.users.exists() and reservation_refreshed.buyer not in discount_obj.users.all():
                logger.warning(f"❌ کاربر {reservation_refreshed.buyer.phone_number} مجاز به استفاده از کد تخفیف {discount_obj.code} نیست.")
                return False

            user_level = getattr(getattr(reservation_refreshed.buyer, 'natural_profile', None), 'level', None)
            if discount_obj.user_level and discount_obj.user_level != user_level:
                logger.warning(f"❌ سطح کاربری {user_level} برای کد تخفیف {discount_obj.code} معتبر نیست.")
                return False

            if discount_obj.remaining_uses <= 0:
                logger.warning(f"❌ دفعات استفاده از کد تخفیف {discount_obj.code} به پایان رسیده است. remaining_uses: {discount_obj.remaining_uses}")
                return False

            # این چک را حذف می‌کنیم، زیرا DiscountActivationRecord باید وجود داشته باشد
            # و در صورت عدم وجود آن، رکورد ایجاد شود یا خطا داده شود.
            # اگر DiscountActivationRecord از قبل برای این کاربر و کد تخفیف ایجاد شده و reward_claimed == True باشد، یعنی قبلا استفاده شده.
            # این موضوع در قسمت پایین‌تر بررسی می‌شود.
            # if reservation_refreshed.buyer in discount_obj.activated_users.all():
            #     logger.warning(f"❌ کاربر {reservation_refreshed.buyer.phone_number} قبلاً از کد تخفیف {discount_obj.code} استفاده کرده است.")
            #     return False

            activation_filter = {
                'user': reservation_refreshed.buyer,
                'discount_type': discount_type,
            }
            if discount_type == 'room':
                activation_filter['room_discount_code'] = discount_obj
            else:
                activation_filter['hotel_discount_code'] = discount_obj

            # استفاده از get() به جای filter().first() برای اطمینان از وجود رکورد و یا خطا در صورت عدم وجود
            # این رکورد باید قبلا در مرحله اعمال کد تخفیف (قبل از پرداخت) ایجاد شده باشد.
            try:
                activation_record = DiscountActivationRecord.objects.select_for_update().get(**activation_filter)
            except DiscountActivationRecord.DoesNotExist:
                logger.error(f"❌ رکورد فعال‌سازی برای کد تخفیف {discount_obj.code} و کاربر {reservation_refreshed.buyer.phone_number} یافت نشد. این رکورد باید در زمان اعمال تخفیف ایجاد شده باشد.")
                return False

            if activation_record.reward_claimed:
                logger.warning(f"❌ رکورد فعال‌سازی برای کد تخفیف {discount_obj.code} قبلاً استفاده شده است.")
                return False

            logger.info(f"🟡 مصرف کد تخفیف {discount_obj.code} - remaining_uses قبل: {discount_obj.remaining_uses}")
            
            if discount_type == 'room':
                RoomDiscountCode.objects.filter(pk=discount_obj.pk).update(remaining_uses=F('remaining_uses') - 1)
            else:
                HotelDiscountCode.objects.filter(pk=discount_obj.pk).update(remaining_uses=F('remaining_uses') - 1)
            
            discount_obj.refresh_from_db()
            
            discount_obj.activated_users.add(reservation_refreshed.buyer)
            
            logger.info(f"🟢 کد تخفیف {discount_obj.code} ذخیره شد - remaining_uses بعد: {discount_obj.remaining_uses}")
            
            activation_record.reward_claimed = True
            set_skip_points_and_sms(True)
            activation_record.save(update_fields=['reward_claimed'])
            set_skip_points_and_sms(False)
            logger.info(f"🟢 رکورد فعال‌سازی برای کاربر {reservation_refreshed.buyer.phone_number} به‌روزرسانی شد.")
            
            reservation_refreshed.discount_processed = True
            reservation_refreshed._skip_price_calculation_on_save = True 
            reservation_refreshed.save(update_fields=['discount_processed'])
            del reservation_refreshed._skip_price_calculation_on_save
            
            logger.info(f"✅ کد تخفیف {discount_obj.code} با موفقیت اعمال شد.")
            logger.info(f"✅ remaining_uses نهایی: {discount_obj.remaining_uses}")
            logger.info(f"✅ کاربر {reservation_refreshed.buyer.phone_number} به activated_users اضافه شد.")
            logger.info(f"✅ رزرو {reservation_refreshed.tracking_code} پردازش شد.")
            
            return True

    except Exception as e:
        logger.error(f"🔴 خطا در پردازش کد تخفیف برای رزرو {reservation.tracking_code}: {e}")
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")
        return False
    finally:
        cache.delete(cache_key)


def _process_wallet_withdrawal(reservation):
    """
    برداشت از کیف پول با اطمینان از ذخیره تیک و کم کردن موجودی در یک تراکنش اتمیک
    """
    logger.info(f"🟡 _process_wallet_withdrawal فراخوانی شد برای رزرو {reservation.tracking_code}")
    
    cache_key = f"wallet_withdrawal_lock_{reservation.tracking_code}"
    if cache.get(cache_key):
        logger.info(f"Wallet withdrawal for {reservation.tracking_code} skipped due to lock.")
        return False

    try:
        with transaction.atomic():
            logger.info(f"🟡 شروع تراکنش برداشت کیف پول برای رزرو {reservation.tracking_code}")
            reservation_refreshed = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)

            if reservation_refreshed.wallet_withdrawn:
                logger.info(f"Wallet already withdrawn for reservation {reservation_refreshed.tracking_code}, skipping.")
                return True

            if reservation_refreshed.wallet_withdrawal_amount <= 0:
                logger.info(f"No wallet withdrawal amount for reservation {reservation_refreshed.tracking_code}.")
                return True

            cache.set(cache_key, True, timeout=60)

            wallet = Wallet.objects.select_for_update().get(user=reservation_refreshed.buyer)
            withdrawal_amount = int(reservation_refreshed.wallet_withdrawal_amount)

            logger.info(f"🟢 برداشت از کیف پول: موجودی فعلی {wallet.balance} | مبلغ برداشت {withdrawal_amount}")

            if wallet.balance < withdrawal_amount:
                logger.warning(f"موجودی کیف پول کافی نیست! موجودی: {wallet.balance} | مبلغ درخواستی: {withdrawal_amount}")
                return False

            # ابتدا ذخیره تیک برداشت کیف پول
            reservation_refreshed.wallet_withdrawn = True
            reservation_refreshed._skip_price_calculation_on_save = True
            reservation_refreshed.save(update_fields=['wallet_withdrawn'])
            del reservation_refreshed._skip_price_calculation_on_save
            logger.info(f"✅ فلگ wallet_withdrawn ذخیره شد.")

            # سپس کم کردن موجودی کیف پول
            wallet.balance = F('balance') - withdrawal_amount
            wallet.save(update_fields=['balance'])
            wallet.refresh_from_db()
            logger.info(f"✅ موجودی کیف پول پس از برداشت: {wallet.balance}")

            logger.info(f"✅ برداشت کیف پول برای رزرو {reservation_refreshed.tracking_code} با موفقیت انجام شد.")
            return True

    except Wallet.DoesNotExist:
        logger.error(f"❌ کیف پول برای کاربر {reservation.buyer.phone_number} یافت نشد.")
        return False
    except Exception as e:
        logger.error(f"❌ خطا در برداشت کیف پول رزرو {reservation.tracking_code}: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        cache.delete(cache_key)
        logger.info(f"🔵 پایان تراکنش برداشت کیف پول رزرو {reservation.tracking_code}")
        

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
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")

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
                    "points_assigned": reservation.points_assigned,
                    "wallet_withdrawal_amount": int(reservation.wallet_withdrawal_amount),
                    "wallet_withdrawn": reservation.wallet_withdrawn,
                },
            },
        )
        logger.debug(f"اعلان به‌روزرسانی وضعیت برای رزرو {reservation.tracking_code} ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال WebSocket برای رزرو {reservation.tracking_code}: {e}")
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")
        
        

# ===================================================================
# 7. مدیریت کنسلی کاربر
# ===================================================================
@receiver(post_save, sender=UserCancellation)
def handle_user_cancellation_approval(sender, instance, created, **kwargs):
    if created or instance.status != UserCancellation.Status.APPROVED:
        return

    cache_key = f"cancellation_processed_{instance.pk}"
    if cache.get(cache_key):
        logger.info(f"Cancellation {instance.pk} already processed, skipping.")
        return

    try:
        with transaction.atomic():
            cancellation = UserCancellation.objects.select_for_update().get(pk=instance.pk)
            reservation = Reservationhotel.objects.select_for_update().get(pk=cancellation.reservation.pk)

            if reservation.cancellation_refunded_amount > 0:
                cache.set(cache_key, True, 86400)
                logger.info(f"Cancellation {instance.pk} already has refund amount, skipping further processing.")
                return

            reservation.capacity_status = 'rejected'
            reservation.payment_status = 'unpaid'
            reservation.cancellation_requested = True

            penalty_amount, refund_amount = reservation.calculate_cancellation_refund()
            reservation.cancellation_penalty_applied = penalty_amount
            reservation.cancellation_refunded_amount = refund_amount

            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=reservation.buyer)
                wallet.balance = F('balance') + int(refund_amount)
                wallet.save(update_fields=['balance'])
                wallet.refresh_from_db()
                logger.info(f"مبلغ {refund_amount:,} به کیف پول کاربر {reservation.buyer.phone_number} برگشت داده شد. موجودی جدید: {wallet.balance:,}")
            else:
                logger.info(f"مبلغ برگشتی برای کنسلی {reservation.tracking_code} صفر است.")

            reservation._skip_price_calculation_on_save = True 
            reservation.save(update_fields=[
                'capacity_status', 'payment_status', 'cancellation_penalty_applied',
                'cancellation_refunded_amount', 'cancellation_requested'
            ])
            del reservation._skip_price_calculation_on_save

            cache.set(cache_key, True, 86400)
            logger.info(f"کنسلی تأیید شد: {reservation.tracking_code} | جریمه: {penalty_amount:,} | برگشتی: {refund_amount:,}")

    except Exception as e:
        logger.error(f"🔴 خطا در کنسلی {instance.pk}: {e}", exc_info=True)
        logger.error(f"🔴 جزئیات خطا: {traceback.format_exc()}")
    finally:
        if cache.get(cache_key) is None:
            cache.delete(cache_key)