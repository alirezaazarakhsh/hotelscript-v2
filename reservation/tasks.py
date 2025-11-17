# tasks.py
from celery import shared_task
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
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
    بررسی رزروهای pending که تایمرشان تمام شده و هنوز تایید/رد نشده‌اند.
    موجودی اتاق‌های این رزروها را برمی‌گرداند.
    این task باید هر 1 دقیقه اجرا شود.
    """
    logger.info("Starting check_and_reject_expired_reservations task")
    
    # دریافت مدت زمان تأیید رزرو
    approval_duration = ReservationApprovalDuration.objects.first()
    duration_minutes = approval_duration.duration_minutes if approval_duration else 5
    cutoff_time = jdatetime.datetime.now() - jdatetime.timedelta(minutes=duration_minutes)
    
    # پیدا کردن رزروهای pending که قبل از cutoff_time ایجاد شده‌اند
    expired_reservations = Reservationhotel.objects.filter(
        capacity_status='pending',
        created_at__lt=cutoff_time
    )
    
    rejected_count = 0
    for reservation in expired_reservations:
        try:
            with transaction.atomic():
                # قفل کردن رزرو
                res = Reservationhotel.objects.select_for_update().get(pk=reservation.pk)
                
                # اگر هنوز pending است، رد می‌کنیم
                if res.capacity_status == 'pending':
                    res.capacity_status = 'rejected'
                    res.save(update_fields=['capacity_status'])
                    
                    # برگرداندن موجودی اتاق‌ها
                    rooms = ReservationRoom.objects.filter(reservation=res).select_related('room')
                    for r in rooms:
                        room = Room.objects.select_for_update().get(pk=r.room.pk)
                        # برای pending، auto_approved همیشه False است
                        room.revert_inventory_for_cancellation(r.quantity, auto_approval=False)
                        logger.info(f"Reverted inventory for room {room.id}, quantity: {r.quantity}")
                    
                    # حذف کش‌های مربوطه
                    cache_key_approval = f"reservation_approval_timer_{res.tracking_code}"
                    cache_key_payment = f"reservation_payment_timer_{res.tracking_code}"
                    cache.delete_many([cache_key_approval, cache_key_payment])
                    
                    rejected_count += 1
                    logger.info(f"Reservation {res.tracking_code} rejected due to timeout")
        except Exception as e:
            logger.error(f"Error rejecting reservation {reservation.tracking_code}: {str(e)}")
    
    logger.info(f"check_and_reject_expired_reservations completed. Rejected {rejected_count} reservations.")
    return rejected_count