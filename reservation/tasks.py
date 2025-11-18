# tasks.py
from celery import shared_task
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from authentication import models
from .models import RoomDatePrice, Reservationhotel, ReservationRoom, Room, ReservationApprovalDuration
import jdatetime

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_prices():
    """حذف خودکار رکوردهای منقضی‌شده بر اساس تاریخ پایان یا تاریخ انقضای تخفیف"""
    current_date = jdatetime.datetime.now().date()
    expired_records = RoomDatePrice.objects.filter(
        models.Q(end_date__lt=current_date) | 
        models.Q(discount_type='percentage', discount_date__lt=current_date)
    )
    deleted_count = expired_records.delete()[0]
    print(f"Deleted {deleted_count} expired price records.")

@shared_task
def check_and_reject_expired_reservations():
    """
    اسکن دوره‌ای رزروهایی که:
      - هنوز پرداخت نشده‌اند (payment_status != paid)
      - یا وضعیت ظرفیتشان مشخص نشده (capacity_status == pending)
      - بیش از مدت مجاز (defaults to 15 mins) از زمان ایجادشان گذشته است.
    در این حالت رزرو لغو (rejected) و موجودی اتاق‌ها دقیقاً به همان bucket اولیه (count یا auto_approved_count) برگردانده می‌شود.
    پیشنهاد: اجرای هر دقیقه توسط celery beat.
    """
    logger.info("Starting enhanced check_and_reject_expired_reservations task")

    approval_duration = ReservationApprovalDuration.objects.first()
    duration_minutes = approval_duration.duration_minutes if approval_duration else 15  # default 15

    cutoff_gregorian = timezone.now() - timedelta(minutes=duration_minutes)
    # created_at در مدل رزرو jDateTimeField است؛ تبدیل به gregorian برای مقایسه امن
    expired_reservations = []
    for r in Reservationhotel.objects.filter(payment_status__in=['pending','unpaid']).exclude(capacity_status='rejected'):
        try:
            created_dt = r.created_at.togregorian() if hasattr(r.created_at, 'togregorian') else r.created_at
            if created_dt < cutoff_gregorian:
                expired_reservations.append(r)
        except Exception:
            continue

    rejected_count = 0
    for reservation in expired_reservations:
        try:
            with transaction.atomic():
                res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
                # دوباره چک تا race condition کم شود
                if res.payment_status == 'paid' or res.capacity_status == 'rejected':
                    continue
                created_dt = res.created_at.togregorian() if hasattr(res.created_at, 'togregorian') else res.created_at
                if created_dt >= cutoff_gregorian:
                    continue

                # لغو رزرو
                res.capacity_status = 'rejected'
                res.save(update_fields=['capacity_status'])

                for r_room in ReservationRoom.objects.filter(reservation=res).select_related('room'):
                    room = Room.objects.select_for_update().get(pk=r_room.room.pk)
                    room.revert_inventory_for_cancellation(r_room.quantity, auto_approval=r_room.was_auto_approved)
                    logger.info(
                        f"Inventory reverted for room {room.id} | qty={r_room.quantity} | auto={r_room.was_auto_approved}"
                    )

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
    اگر پس از اجرا رزرو هنوز پرداخت نشده باشد، لغو و موجودی برگردانده می‌شود.
    این رویکرد latency پایین‌تر نسبت به اسکن سراسری دارد.
    """
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation_id)
            if res.payment_status == 'paid' or res.capacity_status == 'rejected':
                logger.info(f"Reservation {res.tracking_code} already settled before auto cancel.")
                return False
            created_dt = res.created_at.togregorian() if hasattr(res.created_at, 'togregorian') else res.created_at
            if created_dt > timezone.now() - timedelta(minutes=15):
                # هنوز به 15 دقیقه نرسیده؛ رها می‌کنیم (احتمالاً duration تغییر کرده)
                return False

            res.capacity_status = 'rejected'
            res.save(update_fields=['capacity_status'])
            for r_room in ReservationRoom.objects.filter(reservation=res).select_related('room'):
                room = Room.objects.select_for_update().get(pk=r_room.room.pk)
                room.revert_inventory_for_cancellation(r_room.quantity, auto_approval=r_room.was_auto_approved)
            logger.info(f"Reservation {res.tracking_code} auto-cancelled after 15 mins unpaid.")
            return True
    except Reservationhotel.DoesNotExist:
        logger.warning(f"Reservation {reservation_id} not found for auto cancel.")
        return False
    except Exception as e:
        logger.error(f"Error in auto_cancel_unpaid_reservation({reservation_id}): {e}")
        return False