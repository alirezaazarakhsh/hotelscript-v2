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


@shared_task(name="reservation.tasks.cleanup_expired_prices")
def cleanup_expired_prices():
    """حذف رکوردهای منقضی‌شده قیمت"""
    current_date = jdatetime.datetime.now().date()
    expired_records = RoomDatePrice.objects.filter(
        Q(end_date__lt=current_date) | 
        Q(discount_type='percentage', discount_date__lt=current_date)
    )
    deleted_count = expired_records.delete()[0]
    logger.info(f"Deleted {deleted_count} expired price records.")


@shared_task(name="reservation.tasks.check_and_reject_expired_reservations")
def check_and_reject_expired_reservations():
    """
    بررسی و رد رزروهایی که مدت زمان تایید آنها منقضی شده است
    (مورد استفاده در Celery Beat Schedule)
    """
    try:
        duration_obj = ReservationApprovalDuration.objects.first()
        duration_min = duration_obj.duration_minutes if duration_obj else 30
        expire_time = timezone.now() - timedelta(minutes=duration_min)

        expired_reservations = Reservationhotel.objects.filter(
            capacity_status='pending',
            created_at__lt=expire_time
        )

        count = 0
        channel_layer = get_channel_layer()

        for res in expired_reservations:
            res.capacity_status = 'rejected'
            res.save(update_fields=['capacity_status'])
            count += 1

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

        if count > 0:
            logger.info(f"تعداد {count} رزرو به دلیل پایان مهلت تایید منقضی و رد شدند.")
        return count
    except Exception as e:
        logger.error(f"Error in check_and_reject_expired_reservations: {e}")
        return 0


@shared_task(name="reservation.tasks.auto_cancel_unpaid_reservation")
def auto_cancel_unpaid_reservation(reservation_id):
    """لغو خودکار رزروهای تاییدشده ولی پرداخت‌نشده بعد از ۱۵ دقیقه"""
    try:
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().get(pk=reservation_id)
            if res.payment_status == 'paid' or res.capacity_status == 'rejected':
                return False

            res.capacity_status = 'rejected'
            res.save(update_fields=['capacity_status'])
            logger.info(f"رزرو {res.tracking_code} به دلیل عدم پرداخت پس از ۱۵ دقیقه منقضی شد.")

            # ارسال پیام وضعیت به وب‌سوکت فرانت‌اند
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


@shared_task(name="reservation.tasks.check_pending_snapptrip_inquiries_task")
def check_pending_snapptrip_inquiries_task():
    """
    بررسی خودکار وضعیت استعلام رزروهای آفلاین اسنپ‌تریپ هر ۲ دقیقه یک‌بار
    به محض تایید هتل در اسنپ، وب‌سوکت فایر شده و تایمر ۹۰۰ ثانیه‌ای پرداخت برای مسافر آغاز می‌شود.
    """
    lock_id = "snapptrip_inquiries_check_lock"
    acquire_lock = cache.add(lock_id, "true", timeout=110)
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

                # در صورت پذیرش ظرفیت توسط هتل در اسنپ:
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

                # در صورت عدم تایید یا نبود ظرفیت هتل:
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


@shared_task(name="reservation.tasks.auto_sync_snapptrip_prices_task")
def auto_sync_snapptrip_prices_task():
    """
    بروزرسانی خودکار و دوره‌ای قیمت و تقویم ۳۰ روز آینده تمام هتل‌های فعال اسنپ‌تریپ
    مجهز به قفل کش (Cache Lock) برای جلوگیری از تداخل اجراهای همزمان
    """
    lock_id = "auto_sync_snapptrip_prices_lock"
    # قفل به مدت ۴۵ دقیقه برای اتمام کامل حلقه
    acquire_lock = cache.add(lock_id, "true", timeout=2700)
    if not acquire_lock:
        logger.warning("تسک بروزرسانی قیمت‌های اسنپ‌تریپ هم‌اکنون در حال اجراست؛ تسک جدید متوقف شد.")
        return False

    try:
        snapp_hotels = Hotel.objects.filter(
            is_snapptrip=True,
            snapptrip_hotel_id__isnull=False
        ).exclude(snapptrip_hotel_id="")

        total_hotels = snapp_hotels.count()
        logger.info(f"🔄 شروع بروزرسانی خودکار قیمت و تقویم {total_hotels} هتل متصل به اسنپ...")

        success_count = 0
        failed_count = 0

        for hotel in snapp_hotels:
            try:
                success, msg = sync_hotel_and_rooms_from_snapp(hotel.id)
                if success:
                    success_count += 1
                    logger.info(f"✅ هتل '{hotel.name}' (شناسه اسنپ: {hotel.snapptrip_hotel_id}) با موفقیت بروز شد.")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ هتل '{hotel.name}': {msg}")
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ خطای پیش‌بینی نشده در هتل '{hotel.name}': {e}")

            # مکث کوتاه ۱ ثانیه‌ای برای رعایت سقف درخواست وب‌سرویس اسنپ
            time.sleep(1)

        logger.info(f"🏁 پایان بروزرسانی قیمت‌ها: {success_count} موفق، {failed_count} ناموفق از مجموع {total_hotels} هتل.")
        return True

    finally:
        cache.delete(lock_id)

# نام جایگزین برای پشتیبانی از فراخوانی‌های قدیمی
auto_sync_snapptrip_hotels_task = auto_sync_snapptrip_prices_task