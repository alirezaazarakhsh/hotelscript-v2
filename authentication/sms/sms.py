import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern


#ارسال otp به شماره تلفن همراه با استفاده از پترن‌های سامانه کاوه نگار
def send_otp_sms(phone_number, code, pattern_section='otp'):
    try:
        # گرفتن تنظیمات سامانه فعال
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("KavenegarSMSSetting not found")
            return False

        # پیدا کردن پترن متناسب با بخش موردنظر و تنظیمات پیامکی
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
            'token': code,
            'type': 'sms',
        }

        api.verify_lookup(params)
        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')
    
    return False





# ارسال پیامک خوش‌آمدگویی پس از لاگین کاربر به شماره تلفن همراه با استفاده از پترن‌های سامانه کاوه نگار
logger = logging.getLogger(__name__)

def send_welcome_sms(phone_number, full_name, pattern_section='welcome'):
    """
    ارسال SMS خوش‌آمدگویی
    """
    logger.info(f"Attempting to send welcome SMS to {phone_number} with full_name={full_name}")
    try:
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found")
            return False

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found")
            return False

        logger.debug(f"Using pattern code: {template_obj.pattern_code}")
        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': full_name,
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        logger.info(f"Kavenegar response for {phone_number}: {response}")
        return True

    except APIException as e:
        logger.error(f"APIException in send_welcome_sms: {e}")
        return False
    except HTTPException as e:
        logger.error(f"HTTPException in send_welcome_sms: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_welcome_sms: {e}")
        return False





# ارسال پیامک خروج از اکانت کاربری به شماره تلفن همراه با استفاده از پترن‌های سامانه کاوه نگار
def send_logout_sms(phone_number, full_name, pattern_section='logout'):
    try:
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("KavenegarSMSSetting not found")
            return False

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
            'token': full_name,
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Response from Kavenegar:", response)

        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')

    return False
