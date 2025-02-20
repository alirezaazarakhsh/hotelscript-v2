from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_future_datetime(value):
    if value <= timezone.now():
        raise ValidationError("تاریخ باید برای آینده باشد.")
