import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from authentication.models import Admin

logger = logging.getLogger(__name__)

def send_room_availability_sms(room_name, status, hotel_name=None, pattern_section='roomavailability'):
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

        admins = Admin.objects.filter(sms_patterns=template_obj).select_related('base_user')
        logger.debug(f"Admins: {list(admins)}")
        if not admins.exists():
            logger.error(f"No admins found with pattern '{pattern_section}' activated.")
            return False

        api = KavenegarAPI(api_setting.api_token)
        any_success = False

        for admin in admins:
            phone_number = getattr(admin.base_user, 'phone_number', None)
            logger.debug(f"Admin: {admin}, Phone: {phone_number}")
            if not phone_number:
                logger.warning(f"No phone number found for admin {admin}. Skipping.")
                continue

            admin_name = f"{admin.first_name or ''}{admin.last_name or ''}".strip() or "ادمین"
            admin_name = admin_name[:20]
            room_full_name = room_name[:20]  # اسم کامل + ایدی، محدود به 20 کاراکتر
            status_trimmed = status[:20]

            params = {
                'receptor': phone_number,
                'template': template_obj.pattern_code,
                'token': admin_name,
                'token10': room_full_name,
                'token3': status_trimmed,
                'type': 'sms',
            }
            logger.debug(f"Sending SMS to {phone_number} with params: {params}")

            try:
                response = api.verify_lookup(params)
                logger.info(f"SMS sent to {phone_number}. Response: {response}")
                any_success = True
            except APIException as e:
                logger.error(f"APIException for {phone_number}: {str(e)}")
            except HTTPException as e:
                logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return any_success

    except Exception as e:
        logger.error(f"Unexpected error in send_room_availability_sms: {str(e)}", exc_info=True)
        return False