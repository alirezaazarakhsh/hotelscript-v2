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
    ReservationApprovalDuration
)

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_prices():
    """حذف رکوردهای منقضی‌شده قیمت"""
    current_date = jdatetime.datetime.now().date()
    expired_records = RoomDatePrice.objects.filter(
        Q(end_date__lt=current_date) | 
        Q(discount_type='percentage', discount_date__lt=current_date)
    )
    deleted_count = expired_records.delete()[0]
    logger.info(f"Deleted {deleted_count} expired price records.")


@shared_task
def auto_cancel_unpaid_reservation(reservation_id):
    """لغو خودکار رزروهای پرداخت‌نشده بعد از ۱۵ دقیقه"""
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation_id)
            if res.payment_status == 'paid' or res.capacity_status == 'rejected':
                return False

            res.capacity_status = 'rejected'
            res.save(update_fields=['capacity_status'])
            logger.info(f"رزرو {res.tracking_code} به دلیل عدم پرداخت پس از ۱۵ دقیقه منقضی شد.")

            # ارسال وب‌سوکت انقضا
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"reservation_{res.tracking_code}",
                {
                    "type": "status_update",
                    "message": {
                        "capacity_status": "rejected",
                        "payment_status": res.payment_status,
                        "timer": None
                    },
                },
            )
            return True
    except Reservationhotel.DoesNotExist:
        return False
    except Exception as e:
        logger.error(f"Error in auto_cancel_unpaid_reservation: {e}")
        return False


@shared_task
def check_pending_snapptrip_inquiries_task():
    """
    بررسی خودکار رزروهای استعلامی اسنپ:
    به محض تایید هتل در اسنپ، وضعیت confirmed شده و وب‌سوکت با تایمر ۹۰۰ ثانیه روشن می‌شود.
    """
    lock_id = "snapptrip_inquiries_check_lock"
    acquire_lock = cache.add(lock_id, "true", timeout=120)
    if not acquire_lock:
        return

    try:
        pending_snapps = Reservationhotel.objects.select_related('buyer').filter(
            is_snapptrip_reservation=True,
            capacity_status='pending',
            snapp_reservation_code__isnull=False
        )

        channel_layer = get_channel_layer()

        for res in pending_snapps:
            try:
                status_in_snapp, _ = get_snapptrip_booking_status(res.snapp_reservation_code)
                res.snapp_status = status_in_snapp

                user_wallet = getattr(res.buyer, 'wallet', None)
                user_balance = int(user_wallet.balance) if user_wallet else 0

                # اگر هتل ظرفیت را تایید کرد:
                if status_in_snapp in ['availability_confirmed', 'confirmed', 'payment_on']:
                    res.capacity_status = 'confirmed'
                    res.save(update_fields=['capacity_status', 'snapp_status'])

                    async_to_sync(channel_layer.group_send)(
                        f"reservation_{res.tracking_code}",
                        {
                            "type": "status_update",
                            "message": {
                                "capacity_status": "confirmed",
                                "payment_status": res.payment_status,
                                "snapp_status": res.snapp_status,
                                "wallet_balance": user_balance,
                                "timer": 900
                            },
                        },
                    )
                    logger.info(f"✅ رزرو استعلامی {res.tracking_code} در اسنپ تایید شد و وب‌سوکت فایر شد.")

                # اگر هتل ظرفیت نداشت و رد شد:
                elif status_in_snapp in ['availability_rejected', 'failed', 'expired']:
                    res.capacity_status = 'rejected'
                    res.save(update_fields=['capacity_status', 'snapp_status'])

                    async_to_sync(channel_layer.group_send)(
                        f"reservation_{res.tracking_code}",
                        {
                            "type": "status_update",
                            "message": {
                                "capacity_status": "rejected",
                                "payment_status": res.payment_status,
                                "snapp_status": res.snapp_status,
                                "wallet_balance": user_balance,
                                "timer": None
                            },
                        },
                    )
                else:
                    res.save(update_fields=['snapp_status'])

                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Error checking inquiry for {res.tracking_code}: {e}")

    finally:
        cache.delete(lock_id)