# tasks.py
from celery import shared_task

from authentication import models
from .models import RoomDatePrice
import jdatetime

@shared_task
def cleanup_expired_prices():
    current_date = jdatetime.datetime.now().date()
    RoomDatePrice.objects.filter(
        models.Q(end_date__lt=current_date) | 
        models.Q(discount_type='percentage', discount_date__lt=current_date)
    ).delete()