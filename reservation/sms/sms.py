import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from authentication.models import Admin

logger = logging.getLogger(__name__)

def send_room_availability_sms(room_name, status, pattern_section='roomavailability'):
    try:
        # گرفتن تنظیمات سامانه فعال
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found")
            return False

        # پیدا کردن پترن متناسب با بخش موردنظر
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found")
            return False

        # پیدا کردن ادمین‌هایی که پترن room_availability را فعال کرده‌اند
        admins = Admin.objects.filter(sms_patterns=template_obj).select_related('base_user')
        if not admins:
            logger.error("No admins found with pattern 'room_availability' activated")
            return False

        api = KavenegarAPI(api_setting.api_token)
        success = False

        # ارسال پیامک به هر ادمین
        for admin in admins:
            phone_number = admin.base_user.phone_number
            if not phone_number:
                logger.warning(f"No phone number found for admin {admin}")
                continue

            # محدود کردن طول نام ادمین برای جلوگیری از خطای طول
            admin_name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "ادمین"
            admin_name = admin_name[:20]  # محدود کردن به 20 کاراکتر

            params = {
                'receptor': phone_number,
                'template': template_obj.pattern_code,
                'token': admin_name,    # توکن اول: نام ادمین (محدود شده)
                'token2': room_name[:20],  # توکن دوم: نام اتاق (محدود شده)
                'token3': status[:20],     # توکن سوم: وضعیت (محدود شده)
                'type': 'sms',
            }

            try:
                response = api.verify_lookup(params)
                logger.info(f"Response from Kavenegar for {phone_number}: {response.describe() if hasattr(response, 'describe') else str(response)}")
                success = True
            except APIException as e:
                logger.error(f"APIException for {phone_number}: {str(e)} - Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
            except HTTPException as e:
                logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return success

    except Exception as e:
        logger.error(f"Unexpected error in send_room_availability_sms: {str(e)}", exc_info=True)
        return False