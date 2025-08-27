import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern


logger = logging.getLogger(__name__)

def send_wallet_increase_sms(user, amount_increased, pattern_section='walletincrease'):
    try:
        logger.debug(f"Starting send_wallet_increase_sms for user: {user}, amount: {amount_increased}")
        if amount_increased <= 0:
            print(f"Amount increased is zero or negative ({amount_increased}). Skipping SMS.")
            return False

        # دریافت تنظیمات API
        api_setting = KavenegarSMSSetting.objects.filter(is_active=True).first()
        if not api_setting:
            print("KavenegarSMSSetting not found or not active")
            return False

        # دریافت الگوی SMS
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj or not template_obj.pattern_code:
            print(f"SMSPattern for section '{pattern_section}' not found or invalid pattern_code")
            return False

        # دریافت موجودی کیف پول
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet:
            print(f"No wallet found for user {user}")
            return False
        new_balance = wallet.balance

        # دریافت شماره تلفن
        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            print("User phone number not found")
            return False

        # اصلاح فرمت شماره تلفن
        if not phone_number.startswith('+98'):
            phone_number = '+98' + phone_number.lstrip('0')
        logger.debug(f"Formatted phone number: {phone_number}")

        # آماده‌سازی نام کاربر
        user_name = f"{user.natural_profile.first_name or ''} {user.natural_profile.last_name or ''}".strip() or phone_number[:20]
        user_name = user_name[:20]
        amount_str = f"{amount_increased:,}"[:20]
        balance_str = f"{new_balance:,}"[:20]

        # آماده‌سازی درخواست API
        api = KavenegarAPI(api_setting.api_token)
        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user_name,      # %token -> نام کاربر
            'token2': amount_str,    # %token2 -> مبلغ افزایش‌یافته
            'token3': balance_str,   # %token3 -> موجودی فعلی
            'type': 'sms',
        }

        # ارسال درخواست
        response = api.verify_lookup(params)
        print(f"Response from Kavenegar (wallet increase): {response}")
        logger.info(f"SMS sent to {phone_number}. Response: {response}")
        return True

    except APIException as e:
        print(f"APIException in send_wallet_increase_sms: {str(e)}")
        logger.error(f"APIException for {phone_number}: {str(e)}")
        return False
    except HTTPException as e:
        print(f"HTTPException in send_wallet_increase_sms: {str(e)}")
        logger.error(f"HTTPException for {phone_number}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error in send_wallet_increase_sms: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False