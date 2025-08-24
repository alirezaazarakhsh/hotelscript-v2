import logging
from venv import logger
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from bashgah_moshtarian.models import CustomerClubPoint
from celery import shared_task


def send_customer_club_point_sms(user, added_points, pattern_section='customerclubpoint'):
    """
    افزایش امتیاز کاربر و ارسال SMS
    """
    try:
        # دریافت یا ایجاد رکورد امتیاز کاربر
        customer_points, created = CustomerClubPoint.objects.get_or_create(user=user)

        # افزایش امتیاز
        customer_points.points += added_points
        customer_points.save()

        # شماره تلفن
        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            print(f"No phone number found for user {user}")
            return False

        if phone_number.startswith("0"):
            phone_number = "98" + phone_number[1:]

        # تنظیمات Kavenegar
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("KavenegarSMSSetting not found")
            return False

        # پترن پیامک
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            print(f"SMSPattern for section '{pattern_section}' not found")
            return False

        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user.first_name or "کاربر",
            'token2': str(added_points),
            'token3': str(customer_points.points),
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Kavenegar response:", response)
        return True

    except APIException as e:
        print(f"APIException: {e}")
    except HTTPException as e:
        print(f"HTTPException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return False




# اس ام اس دریافت هدیه ثبت‌نام برای باشگاه مشتریان
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_registration_gift_sms(self, phone_number, added_points, pattern_section='registrationgift'):
    """
    ارسال SMS هدیه ثبت‌نام با retry خودکار در صورت خطا
    """
    logger.info(f"Starting send_registration_gift_sms task for {phone_number} with points={added_points}")

    try:
        # تبدیل شماره به فرمت بین‌المللی
        if phone_number.startswith("0"):
            phone_number = "98" + phone_number[1:]
        logger.debug(f"Converted phone number to {phone_number}")

        # گرفتن تنظیمات Kavenegar
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found")
            raise self.retry(countdown=10, exc=Exception("KavenegarSMSSetting missing"))

        # پیدا کردن template پیامک
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found")
            raise self.retry(countdown=10, exc=Exception(f"Template '{pattern_section}' missing"))

        logger.debug(f"Using template code: {template_obj.pattern_code}")
        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': str(added_points),
            'type': 'sms',
        }

        # ارسال SMS
        response = api.verify_lookup(params)
        logger.info(f"Gift SMS sent successfully to {phone_number}. Response: {response}")
        return True

    except (APIException, HTTPException) as e:
        logger.error(f"Kavenegar API error for {phone_number}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Unexpected error in send_registration_gift_sms for {phone_number}: {e}")
        raise self.retry(exc=e)
