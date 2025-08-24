from celery import shared_task
import time
from bashgah_moshtarian.sms.sms import send_registration_gift_sms
from authentication.sms.sms import send_welcome_sms
from .models import BaseUser

@shared_task
def send_welcome_and_gift_sms(phone_number, full_name, is_new_user):
    """
    ارسال SMS خوش‌آمدگویی و هدیه ثبت‌نام با تأخیر برای کاربران جدید
    """
    # ارسال SMS خوش‌آمدگویی
    send_welcome_sms(phone_number, full_name)
    
    # اگر کاربر جدید است، بعد از ۵ ثانیه SMS هدیه ثبت‌نام را ارسال کن
    if is_new_user:
        time.sleep(5)  # تأخیر ۵ ثانیه‌ای
        try:
            user = BaseUser.objects.get(phone_number=phone_number)
            send_registration_gift_sms(user, 300)
        except BaseUser.DoesNotExist:
            print(f"User with phone number {phone_number} not found")