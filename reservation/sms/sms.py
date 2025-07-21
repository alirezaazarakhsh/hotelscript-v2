import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from authentication.models import Admin

logger = logging.getLogger(__name__)

def send_room_availability_sms(room_name, status, pattern_section='roomavailability'):
    try:
        # گرفتن تنظیمات سامانه پیامکی کاوه نگار (اولین نمونه)
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found.")
            return False

        # پیدا کردن پترن پیامک مطابق بخش درخواست شده
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found.")
            return False

        # پیدا کردن ادمین‌هایی که این پترن برای آن‌ها فعال است
        admins = Admin.objects.filter(sms_patterns=template_obj).select_related('base_user')
        if not admins.exists():
            logger.error(f"No admins found with pattern '{pattern_section}' activated.")
            return False

        api = KavenegarAPI(api_setting.api_token)
        any_success = False

        # ارسال پیامک به هر ادمین
        for admin in admins:
            phone_number = getattr(admin.base_user, 'phone_number', None)
            if not phone_number:
                logger.warning(f"No phone number found for admin {admin}. Skipping.")
                continue

            # محدود کردن طول رشته‌ها به 20 کاراکتر (مطابق محدودیت کاوه نگار)
            admin_name = f"{admin.first_name or ''} {admin.last_name or ''}".strip() or "ادمین"
            admin_name = admin_name[:20]
            room_name_trimmed = room_name[:20]
            status_trimmed = status[:20]

            params = {
                'receptor': phone_number,
                'template': template_obj.pattern_code,
                'token': admin_name,
                'token2': room_name_trimmed,
                'token3': status_trimmed,
                'type': 'sms',
            }

            try:
                response = api.verify_lookup(params)
                logger.info(f"SMS sent to {phone_number}. Response: {response.describe() if hasattr(response, 'describe') else str(response)}")
                any_success = True
            except APIException as e:
                response_text = e.response.text if hasattr(e, 'response') else 'No response'
                logger.error(f"APIException for {phone_number}: {str(e)} - Response: {response_text}")
            except HTTPException as e:
                logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return any_success

    except Exception as e:
        logger.error(f"Unexpected error in send_room_availability_sms: {str(e)}", exc_info=True)
        return False
