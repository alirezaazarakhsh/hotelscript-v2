# tasks.py
import logging
import time
from datetime import timedelta
import jdatetime

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from reservation.snapptrip_service import (
    sync_hotel_and_rooms_from_snapp,
    get_snapptrip_booking_status
)
from .models import (
    Hotel,
    RoomDatePrice,
    Reservationhotel,
    ReservationRoom,
    Room,
    ReservationApprovalDuration
)

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_prices():
    """حذف خودکار رکوردهای منقضی‌شده بر اساس تاریخ پایان یا تاریخ انقضای تخفیف"""
    current_date = jdatetime.datetime.now().date()
    expired_records = RoomDatePrice.objects.filter(
        Q(end_date__lt=current_date) | 
        Q(discount_type='percentage', discount_date__lt=current_date)
    )
    deleted_count = expired_records.delete()[0]
    logger.info(f"Deleted {deleted_count} expired price records.")


@shared_task
def check_and_reject_expired_reservations():
    """
    اسکن دوره‌ای رزروهایی که:
      - هنوز پرداخت نشده‌اند (payment_status != paid)
      - یا وضعیت ظرفیتشان مشخص نشده (capacity_status == pending)
      - بیش از مدت مجاز (پیش‌فرض ۱۵ دقیقه) از زمان ایجادشان گذشته است.
    در این حالت رزرو لغو (rejected) می‌شود.
    """
    logger.info("Starting enhanced check_and_reject_expired_reservations task")

    approval_duration = ReservationApprovalDuration.objects.first()
    duration_minutes = approval_duration.duration_minutes if approval_duration else 15

    now = timezone.now()
    expired_reservations = []

    for r in Reservationhotel.objects.filter(capacity_status='pending', payment_status__in=['pending', 'unpaid']):
        try:
            cache_key_approval = f"reservation_approval_timer_{r.tracking_code}"
            cache_value = cache.get(cache_key_approval)
            if cache_value:
                try:
                    expires_at_ts = float(cache_value)
                    if expires_at_ts <= now.timestamp():
                        expired_reservations.append(r)
                    continue
                except Exception:
                    logger.exception(f"Invalid cache value for {cache_key_approval}: {cache_value}")

            created_dt = r.created_at.togregorian() if hasattr(r.created_at, 'togregorian') else r.created_at
            cutoff_gregorian = now - timedelta(minutes=duration_minutes)
            if created_dt < cutoff_gregorian:
                expired_reservations.append(r)
        except Exception:
            continue

    rejected_count = 0
    for reservation in expired_reservations:
        try:
            with transaction.atomic():
                res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
                if res.payment_status == 'paid' or res.capacity_status != 'pending':
                    continue

                cache_key_approval = f"reservation_approval_timer_{res.tracking_code}"
                cache_value = cache.get(cache_key_approval)
                if cache_value:
                    try:
                        expires_at_ts = float(cache_value)
                        if expires_at_ts > now.timestamp():
                            continue
                    except Exception:
                        logger.exception(f"Invalid cache value for {cache_key_approval}: {cache_value}")
                else:
                    created_dt = res.created_at.togregorian() if hasattr(res.created_at, 'togregorian') else res.created_at
                    if created_dt >= (now - timedelta(minutes=duration_minutes)):
                        continue

                res.capacity_status = 'rejected'
                res.save(update_fields=['capacity_status'])

                cache_key_approval = f"reservation_approval_timer_{res.tracking_code}"
                cache_key_payment = f"reservation_payment_timer_{res.tracking_code}"
                cache.delete_many([cache_key_approval, cache_key_payment])

                rejected_count += 1
                logger.info(f"Reservation {res.tracking_code} auto-rejected after {duration_minutes} mins (unpaid/pending)")
        except Exception as e:
            logger.error(f"Error auto-rejecting reservation {reservation.tracking_code}: {e}")

    logger.info(f"Enhanced expiration check complete. Rejected {rejected_count} reservations.")
    return rejected_count


@shared_task
def auto_cancel_unpaid_reservation(reservation_id):
    """
    تسک اختصاصی که هنگام ایجاد رزرو با countdown=15m صف می‌شود.
    اگر پس از اجرا رزرو هنوز پرداخت نشده باشد، لغو می‌شود.
    """
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation_id)
            if res.payment_status == 'paid' or res.capacity_status != 'pending':
                logger.info(f"Reservation {res.tracking_code} already settled or not pending before auto cancel.")
                return False

            now = timezone.now()
            cache_key_approval = f"reservation_approval_timer_{res.tracking_code}"
            cache_value = cache.get(cache_key_approval)
            if cache_value:
                try:
                    expires_at_ts = float(cache_value)
                    if expires_at_ts > now.timestamp():
                        return False
                except Exception:
                    logger.exception(f"Invalid cache value for {cache_key_approval}: {cache_value}")
            else:
                created_dt = res.created_at.togregorian() if hasattr(res.created_at, 'togregorian') else res.created_at
                if created_dt > now - timedelta(minutes=15):
                    return False

            res.capacity_status = 'rejected'
            res.save(update_fields=['capacity_status'])
            logger.info(f"Reservation {res.tracking_code} auto-cancelled after 15 mins unpaid.")
            return True
    except Reservationhotel.DoesNotExist:
        logger.warning(f"Reservation {reservation_id} not found for auto cancel.")
        return False
    except Exception as e:
        logger.error(f"Error in auto_cancel_unpaid_reservation({reservation_id}): {e}")
        return False


@shared_task
def auto_sync_snapptrip_hotels_task():
    """
    تسک زمان‌بندی‌شده Celery:
    اتاق‌های هتل‌های فعال اسنپ را به نوبت آپدیت می‌کند.
    مجهز به قفل توزیع‌شده ردیس برای جلوگیری از هم‌پوشانی و خطای Read timed out.
    """
    lock_id = "snapptrip_auto_sync_active_lock"
    # قفل موقت برای ۱۰ دقیقه تا ورکر دیگری همزمان اجرا نشود
    acquire_lock = cache.add(lock_id, "true", timeout=600)

    if not acquire_lock:
        logger.info("تسک همگام‌سازی اسنپ در حال حاضر توسط ورکر دیگری در حال اجراست؛ این نوبت لغو شد.")
        return

    try:
        active_snapp_hotels = Hotel.objects.filter(is_snapptrip=True, snapptrip_hotel_id__isnull=False)

        for hotel in active_snapp_hotels:
            try:
                success, msg = sync_hotel_and_rooms_from_snapp(hotel.id)
                if success:
                    logger.info(f"✅ بروزرسانی خودکار هتل {hotel.name}: {msg}")
                else:
                    logger.warning(f"⚠️ {hotel.name}: {msg}")

                # مکث ۱ ثانیه‌ای بین هتل‌ها برای احترام به سرور اسنپ
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"❌ خطا در بروزرسانی هتل {hotel.name}: {e}")
    finally:
        cache.delete(lock_id)


@shared_task
def check_pending_snapptrip_inquiries_task():
    """
    بررسی خودکار رزروهای نیازمند استعلام از اسنپ:
    وضعیت رزروهای معلق (pending) را از اسنپ استعلام می‌کند.
    اگر هتل ظرفیت را تایید کرد، وضعیت سایت شما confirmed شده و دکمه پرداخت روشن می‌شود.
    """
    lock_id = "snapptrip_inquiries_check_lock"
    acquire_lock = cache.add(lock_id, "true", timeout=120)

    if not acquire_lock:
        return

    try:
        pending_snapps = Reservationhotel.objects.filter(
            is_snapptrip_reservation=True,
            capacity_status='pending',
            snapp_reservation_code__isnull=False
        )

        channel_layer = get_channel_layer()

        for res in pending_snapps:
            try:
                status_in_snapp = get_snapptrip_booking_status(res.snapp_reservation_code)
                res.snapp_status = status_in_snapp

                # اگر هتل تایید کرد:
                if status_in_snapp in ['availability_confirmed', 'confirmed', 'payment_on']:
                    res.capacity_status = 'confirmed'
                    res.save(update_fields=['capacity_status', 'snapp_status'])

                    # ارسال پیام زنده وب‌سوکت برای روشن شدن دکمه پرداخت
                    async_to_sync(channel_layer.group_send)(
                        f"reservation_{res.tracking_code}",
                        {
                            "type": "status_update",
                            "message": {
                                "capacity_status": "confirmed",
                                "timer": 900
                            },
                        },
                    )
                    logger.info(f"✅ رزرو استعلامی {res.tracking_code} توسط هتل در اسنپ تایید شد!")

                # اگر هتل ظرفیت نداشت و رزرو رد شد:
                elif status_in_snapp in ['availability_rejected', 'failed', 'expired']:
                    res.capacity_status = 'rejected'
                    res.save(update_fields=['capacity_status', 'snapp_status'])

                    async_to_sync(channel_layer.group_send)(
                        f"reservation_{res.tracking_code}",
                        {
                            "type": "status_update",
                            "message": {
                                "capacity_status": "rejected",
                                "timer": None
                            },
                        },
                    )
                    logger.info(f"❌ رزرو استعلامی {res.tracking_code} توسط هتل در اسنپ رد شد.")

                else:
                    # همچنان در حال استعلام (availability_checking)
                    res.save(update_fields=['snapp_status'])

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"خطا در بررسی رزرو استعلامی اسنپ ({res.tracking_code}): {e}")

    finally:
        cache.delete(lock_id)