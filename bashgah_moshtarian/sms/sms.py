import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.db.models import Q
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from authentication.models import BaseUser
from ..models import RoomDiscountCode, ShoppingCenterDiscountCode

logger = logging.getLogger(__name__)

def limit_spaces(text, max_spaces=5):
    spaces_count = text.count(' ')
    if spaces_count <= max_spaces:
        return text
    parts = text.split()
    limited_text = ' '.join(parts[:max_spaces+1])  # max_spaces فاصله ایجاد می‌کند
    return limited_text

def send_discount_code_sms(discount_code, pattern_section='discountcode'):

    try:
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found.")
            return False

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found.")
            return False

        api = KavenegarAPI(api_setting.api_token)
        any_success = False

        # بررسی وجود فیلد user_level در مدل BaseUser
        baseuser_has_user_level = hasattr(BaseUser, 'user_level')

        if discount_code.is_public:
            # اگر فیلد user_level موجود است، فیلتر کن، در غیر این صورت بدون آن فیلتر کن
            if baseuser_has_user_level and discount_code.user_level is not None:
                users = BaseUser.objects.filter(
                    Q(customer_points__points__gte=discount_code.required_points) &
                    (Q(user_level=discount_code.user_level) | Q(user_level__isnull=True))
                ).distinct()
            else:
                users = BaseUser.objects.filter(
                    customer_points__points__gte=discount_code.required_points
                ).distinct()
        else:
            if not discount_code.user:
                logger.error("No user specified for private discount code.")
                return False
            users = [discount_code.user]

        if isinstance(discount_code, RoomDiscountCode):
            try:
                location_name = f"اتاق {discount_code.room.name} از هتل {discount_code.room.hotel.name}"[:50]
            except AttributeError:
                location_name = f"اتاق {discount_code.room.name}"[:50]
        else:
            location_name = f"مرکز خرید {discount_code.shopping_center_name}"[:50]

        location_name = limit_spaces(location_name, max_spaces=5)

        for user in users:
            phone_number = getattr(user, 'phone_number', None)
            if not phone_number:
                logger.warning(f"No phone number found for user {user}. Skipping.")
                continue

            user_name = f"{user.first_name or ''}{user.last_name or ''}".strip() or "کاربر"
            user_name = ''.join(user_name.split())[:20]  # حذف فاصله‌ها و محدود به 20 کاراکتر
            discount_code_str = ''.join(discount_code.code.split())[:8]  # حذف فاصله‌ها در کد تخفیف

            params = {
                'receptor': phone_number,
                'template': template_obj.pattern_code,
                'token': user_name,
                'token2': discount_code_str,
                'token10': location_name,
                'type': 'sms',
            }

            try:
                response = api.verify_lookup(params)
                logger.info(f"SMS sent to {phone_number}. Response: {response}")
                any_success = True
                discount_code.activated_users.add(user)
            except APIException as e:
                logger.error(f"APIException for {phone_number}: {str(e)}")
            except HTTPException as e:
                logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return any_success

    except Exception as e:
        logger.error(f"Unexpected error in send_discount_code_sms: {str(e)}", exc_info=True)
        return False