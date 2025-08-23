# authentication/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BaseUser, NaturalProfile
from config.models import UserLevel
from bashgah_moshtarian.models import CustomerClubPoint
from bashgah_moshtarian.sms.registration_gift_sms import send_registration_gift_sms  # تابع جدید
import threading
import time

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

        # ۳. ایجاد رکورد باشگاه مشتریان با امتیاز اولیه صفر
        customer_points, created_points = CustomerClubPoint.objects.get_or_create(
            user=instance,
            defaults={'points': 0}  # صفر باشد
        )

        if created_points:
            # اضافه کردن امتیاز اولیه بعد از ۳۰ ثانیه و ارسال SMS هدیه ثبت‌نام
            def add_initial_points():
                time.sleep(30)  # تاخیر ۳۰ ثانیه
                initial_points = 300
                customer_points.points += initial_points
                customer_points.save()

                # ارسال SMS با پترن هدیه ثبت‌نام
                sms_result = send_registration_gift_sms(instance, initial_points)
                if sms_result:
                    print(f"امتیاز باشگاه مشتریان برای {instance.phone_number} اضافه شد و SMS هدیه ثبت‌نام ارسال شد.")
                else:
                    print(f"امتیاز باشگاه مشتریان اضافه شد اما SMS هدیه ثبت‌نام ارسال نشد.")

            threading.Thread(target=add_initial_points).start()
        else:
            print(f"کاربر {instance.phone_number} قبلاً امتیاز دریافت کرده است. هیچ امتیازی اضافه نشد.")
