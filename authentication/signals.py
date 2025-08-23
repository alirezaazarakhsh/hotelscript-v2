# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint
from bashgah_moshtarian.sms.sms import send_customer_club_point_sms  # تابع SMS

@receiver(post_save, sender=BaseUser)
def create_user_related_records(sender, instance, created, **kwargs):
    if created:
        # ۱. ساخت سطح میهمان
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')

        # ۲. ساخت پروفایل حقیقی
        profile, created_profile = NaturalProfile.objects.get_or_create(
            base_user=instance,
            defaults={
                'first_name': 'میهمان',
                'last_name': 'عزیز',
                'level': guest_level
            }
        )
        if created_profile:
            print(f"پروفایل جدید برای کاربر {instance.phone_number} ساخته شد.")

        # ۳. ایجاد رکورد باشگاه مشتریان اگر وجود نداشت
        customer_points, created_points = CustomerClubPoint.objects.get_or_create(
            user=instance,
            defaults={'points': 300}
        )

        # فقط اگر رکورد تازه ساخته شده، امتیاز اولیه اضافه و SMS ارسال شود
        if created_points:
            initial_points = 300
            customer_points.points += initial_points
            customer_points.save()

            sms_result = send_customer_club_point_sms(instance, initial_points)
            if sms_result:
                print(f"امتیاز باشگاه مشتریان برای {instance.phone_number} اضافه شد و SMS ارسال شد.")
            else:
                print(f"امتیاز باشگاه مشتریان اضافه شد اما SMS ارسال نشد.")
        else:
            print(f"کاربر {instance.phone_number} قبلاً امتیاز دریافت کرده است. هیچ امتیازی اضافه نشد.")
