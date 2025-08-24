from celery import shared_task
import logging
from bashgah_moshtarian.sms.sms import send_registration_gift_sms as send_gift_sms
from authentication.sms.sms import send_welcome_sms
from .models import BaseUser

logger = logging.getLogger(__name__)

@shared_task
def send_welcome_and_gift_sms(phone_number, full_name, is_new_user):
    """
    ارسال SMS خوش‌آمدگویی و هدیه ثبت‌نام برای کاربران جدید
    """
    logger.info(f"Starting task for sending SMS to {phone_number}, is_new_user={is_new_user}")
    
    # ارسال SMS خوش‌آمدگویی
    success = send_welcome_sms(phone_number, full_name)
    if not success:
        logger.error(f"Failed to send welcome SMS to {phone_number}")
    else:
        logger.info(f"Welcome SMS sent successfully to {phone_number}")
    
    # اگر کاربر جدید است، SMS هدیه ثبت‌نام را با تأخیر ۵ ثانیه ارسال کن
    if is_new_user:
        try:
            send_gift_sms.apply_async((phone_number, 300), countdown=5)
            logger.info(f"Scheduled gift SMS for {phone_number} with 5-second delay")
        except Exception as e:
            logger.error(f"Failed to schedule gift SMS for {phone_number}: {e}")

# تسک تستی برای بررسی ارتباط Celery
@shared_task
def debug_task(x, y):
    logger.warning("🔥 Celery is working! %s + %s", x, y)
    return x + y
