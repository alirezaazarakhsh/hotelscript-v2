import logging
from django.dispatch import receiver
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.db.models import Q
from authentication.models import BaseUser
from bashgah_moshtarian.models import ShoppingCenterDiscountCode
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from django.db.models.signals import m2m_changed




# اس ام اس  هدیه ثبت نام 
def send_registration_gift_sms(phone_number, points, pattern_section='registrationgift'):
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
            'token': points,  # مقدار امتیاز را می‌دهیم
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Response from Kavenegar (registration gift):", response)

        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')

    return False




#اس ام اس افزایش و موجودی امتیاز های کاربر در باشگاه مشتریان
logger = logging.getLogger(__name__)

def send_customer_club_sms(phone_number, user_name, added_points, current_points, pattern_section='customerclubpoint'):
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
            'token': user_name,      # %token -> نام کاربر
            'token2': added_points,  # %token2 -> امتیاز اضافه شده
            'token3': current_points,# %token3 -> موجودی فعلی
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Response from Kavenegar (customer club):", response)
        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')

    return False


# اس ام اس کاهش امتیاز باشگاه مشتریان 

logger = logging.getLogger(__name__)

def send_customer_club_deduct_sms(phone_number, user_name, deducted_points, current_points, pattern_section='customerclubpointdeduct'):
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
            'token': user_name,         
            'token2': deducted_points,  
            'token3': current_points,   
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Response from Kavenegar (deduct customer club):", response)
        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')

    return False




# اس ام اس تخفیف برای اتاق و مراکز خرید 
logger = logging.getLogger(__name__)

def clean_token(value):
    """حذف فاصله و کاراکترهای غیرمجاز از توکن‌های مجاز بدون Space"""
    if not value:
        return "کاربر"  # مقدار پیش‌فرض
    return str(value).replace(" ", "").replace("+", "").replace("-", "")

def send_discount_sms(phone_number, user_name, discount_code, location_name, pattern_section='discountcode'):
    """ارسال SMS تخفیف برای اتاق یا مرکز خرید"""
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

        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': clean_token(user_name),      # %token -> نام کاربر
            'token2': clean_token(discount_code), # %token2 -> کد تخفیف
            'token10': location_name,             # %token10 -> نام اتاق یا مرکز خرید
            'type': 'sms',
        }

        logger.info(f"Sending SMS with params: {params}")
        response = api.verify_lookup(params)
        logger.info(f"Response from Kavenegar (discount): {response}")
        return True

    except APIException as e:
        logger.error(f'APIException: {str(e)} - Details: {e.args}')
    except HTTPException as e:
        logger.error(f'HTTPException: {str(e)} - Details: {e.args}')
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
    return False