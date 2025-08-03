# bashgah_moshtarian/sms/sms.py
import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.db.models import Q
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from authentication.models import BaseUser
from ..models import RoomDiscountCode, ShoppingCenterDiscountCode, CustomerClubPoint

logger = logging.getLogger(__name__)

def send_discount_code_sms(discount_code, pattern_section='discountcode'):
    
    try:
        # دریافت تنظیمات API کاوه‌نگار
        api_setting = KavenegarSMSSetting.objects.first()
        logger.debug(f"API Setting: {api_setting}")
        if not api_setting:
            logger.error("KavenegarSMSSetting not found.")
            return False

        # دریافت پترن پیامک
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        logger.debug(f"SMSPattern: {template_obj}")
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found.")
            return False

        api = KavenegarAPI(api_setting.api_token)
        any_success = False

        # تعیین کاربران هدف
        if discount_code.is_public:
            # برای کد تخفیف عمومی: ارسال به همه کاربرانی که شرایط را دارند
            users = BaseUser.objects.filter(
                Q(customer_points__points__gte=discount_code.required_points) &
                (Q(user_level=discount_code.user_level) | Q(user_level__isnull=True))
            )
        else:
            # برای کد تخفیف شخصی: فقط به کاربر مشخص شده
            if not discount_code.user:
                logger.error("No user specified for private discount code.")
                return False
            users = [discount_code.user]

        logger.debug(f"Users to send SMS: {list(users)}")

        # آماده‌سازی نام مکان (اتاق یا مرکز خرید) برای %token10
        if isinstance(discount_code, RoomDiscountCode):
            try:
                location_name = f"اتاق {discount_code.room.name} از هتل {discount_code.room.hotel.name}"[:50]  # محدود به 50 کاراکتر
            except AttributeError:
                location_name = f"اتاق {discount_code.room.name}"[:50]  # در صورت عدم وجود hotel
        else:  # ShoppingCenterDiscountCode
            location_name = f"مرکز خرید {discount_code.shopping_center_name}"[:50]  # محدود به 50 کاراکتر

        for user in users:
            phone_number = getattr(user, 'phone_number', None)
            logger.debug(f"User: {user}, Phone: {phone_number}")
            if not phone_number:
                logger.warning(f"No phone number found for user {user}. Skipping.")
                continue

            # آماده‌سازی نام کاربر برای %token (بدون فاصله)
            user_name = f"{user.first_name or ''}{user.last_name or ''}".strip() or "کاربر"
            user_name = ''.join(user_name.split())[:20]  # حذف فاصله‌ها و محدود به 20 کاراکتر
            discount_code_str = discount_code.code[:8]  # کد تخفیف برای %token2

            params = {
                'receptor': phone_number,
                'template': template_obj.pattern_code,
                'token': user_name,  # نام کاربر (بدون فاصله)
                'token2': discount_code_str,  # کد تخفیف
                'token10': location_name,  # نام اتاق یا مرکز خرید
                'type': 'sms',
            }
            logger.debug(f"Sending SMS to {phone_number} with params: {params}")

            try:
                response = api.verify_lookup(params)
                logger.info(f"SMS sent to {phone_number}. Response: {response}")
                any_success = True

                # افزودن کاربر به لیست کاربران فعال‌کننده کد تخفیف
                discount_code.activated_users.add(user)
            except APIException as e:
                logger.error(f"APIException for {phone_number}: {str(e)}")
            except HTTPException as e:
                logger.error(f"HTTPException for {phone_number}: {str(e)}")

        return any_success

    except Exception as e:
        logger.error(f"Unexpected error in send_discount_code_sms: {str(e)}", exc_info=True)
        return False