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

from reservation.snapptrip_service import sync_hotel_and_rooms_from_snapp
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
    هر ۱ دقیقه یک‌بار اجرا می‌شود و تمام هتل‌های فعال اسنپ را خودکار آپدیت می‌کند.
    """
    active_snapp_hotels = Hotel.objects.filter(is_snapptrip=True, snapptrip_hotel_id__isnull=False)
    
    for hotel in active_snapp_hotels:
        try:
            success, msg = sync_hotel_and_rooms_from_snapp(hotel.id)
            if success:
                logger.info(f"✅ بروزرسانی خودکار ۱ دقیقه‌ای هتل {hotel.name}: {msg}")
            else:
                logger.warning(f"⚠️ خطای بروزرسانی خودکار هتل {hotel.name}: {msg}")
            
            # مکث کوتاه بین استعلام هتل‌ها برای رعایت سقف درخواست‌های مجاز
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره در تسک خودکار هتل {hotel.name}: {e}")