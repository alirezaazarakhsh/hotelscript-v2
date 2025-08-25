# bashgah_moshtarian/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import CustomerClubPoint
from .sms.sms import send_customer_club_sms, send_customer_club_deduct_sms

# ذخیره مقدار قبلی قبل از تغییر
@receiver(pre_save, sender=CustomerClubPoint)
def store_previous_points(sender, instance, **kwargs):
    if instance.pk:
        old = CustomerClubPoint.objects.get(pk=instance.pk)
        instance._previous_points = old.points
    else:
        instance._previous_points = 0

# بعد از ذخیره، ارسال SMS براساس تغییر امتیاز
@receiver(post_save, sender=CustomerClubPoint)
def send_club_points_sms(sender, instance, created, **kwargs):
    added_points = instance.points - getattr(instance, '_previous_points', 0)

    if added_points > 0:
        # افزایش امتیاز
        send_customer_club_sms(
            phone_number=instance.user.phone_number,
            user_name=instance.user.first_name,
            added_points=added_points,
            current_points=instance.points
        )
    elif added_points < 0:
        # کاهش امتیاز
        deducted_points = abs(added_points)
        send_customer_club_deduct_sms(
            phone_number=instance.user.phone_number,
            user_name=instance.user.first_name,
            deducted_points=deducted_points,
            current_points=instance.points
        )
