# tasks.py
from celery import shared_task

from authentication import models
from .models import RoomDatePrice
import jdatetime
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