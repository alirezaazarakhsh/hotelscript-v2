from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
import logging

from reservation.models import Reservationhotel

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Reservationhotel)
def notify_status_change(sender, instance, created, **kwargs):
    if created:
        logger.info(f"رزرو جدید ایجاد شد: {instance.tracking_code}")
        return

    try:
        previous_status = Reservationhotel.objects.get(pk=instance.pk).status
    except Reservationhotel.DoesNotExist:
        previous_status = None

    if previous_status == instance.status:
        return  # اگر وضعیت تغییر نکرد، پیام نفرست

    # محاسبه تایمر فقط وقتی رزرو وارد حالت pending_admin میشه
    duration_minutes = None
    timer_start = None

    if instance.status == 'pending_admin':
        try:
            from .models import ReservationApprovalDuration
            approval_duration = ReservationApprovalDuration.objects.first()
            duration_minutes = approval_duration.duration_minutes if approval_duration else 5
        except ObjectDoesNotExist:
            duration_minutes = 5

        timer_start = instance.updated_at.isoformat()

    # فقط status و تایمر ارسال شود
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"reservation_{instance.tracking_code}",
        {
            "type": "status_update",
            "message": {
                "status": instance.status,
                "status_display": dict(instance.STATUS_CHOICES).get(instance.status, instance.status),
                "duration_minutes": duration_minutes,
                "timer_start": timer_start,
            }
        }
    )
