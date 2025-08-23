import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern

logger = logging.getLogger(__name__)

def send_customer_club_point_sms(user, added_points, pattern_section='customerclubpoint'):
    """
    ارسال پیامک به کاربر وقتی امتیاز باشگاه مشتریان او افزایش پیدا می‌کند.
    """
    try:
        api_setting = KavenegarSMSSetting.objects.first()
        logger.debug(f"API Setting: {api_setting}")
        if not api_setting:
            logger.error("KavenegarSMSSetting not found.")
            return False

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        logger.debug(f"SMSPattern: {template_obj}")
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found.")
            return False

        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            logger.error(f"No phone number found for user {user}.")
            return False

        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user.first_name or "کاربر",
            'token2': str(added_points),
            'token3': str(user.customer_points.points),
            'type': 'sms',
        }
        logger.debug(f"Sending SMS to {phone_number} with params: {params}")

        try:
            response = api.verify_lookup(params)
            logger.info(f"SMS sent to {phone_number}. Response: {response}")
            return True
        except APIException as e:
            logger.error(f"APIException for {phone_number}: {str(e)}")
        except HTTPException as e:
            logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return False

    except Exception as e:
        logger.error(f"Unexpected error in send_customer_club_point_sms: {str(e)}", exc_info=True)
        return False
