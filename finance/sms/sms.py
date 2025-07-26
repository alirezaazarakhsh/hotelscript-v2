import logging
from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from finance.models import Wallet

logger = logging.getLogger(__name__)

def send_wallet_increase_sms(user, amount_increased, pattern_section='walletincrease'):
    try:
        logger.debug(f"Starting send_wallet_increase_sms for user: {user}, amount: {amount_increased}")
        if amount_increased <= 0:
            logger.warning("Amount increased is zero or negative. Skipping SMS.")
            return False

        api_setting = KavenegarSMSSetting.objects.filter(is_active=True).first()
        if not api_setting:
            logger.error("No active KavenegarSMSSetting found.")
            return False
        logger.debug(f"API setting found: {api_setting.api_token}")

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj or not template_obj.pattern_code:
            logger.error(f"Invalid SMSPattern for section '{pattern_section}'.")
            return False
        logger.debug(f"Template found: {template_obj.pattern_code}")

        if not Wallet.objects.filter(user=user).exists():
            logger.error(f"No wallet found for user {user}.")
            return False
        wallet = Wallet.objects.get(user=user)
        new_balance = wallet.balance
        logger.debug(f"Wallet balance: {new_balance}")

        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            logger.error("User phone number not found.")
            return False
        logger.debug(f"Phone number: {phone_number}")

        user_name = f"{user.natural_profile.first_name or ''} {user.natural_profile.last_name or ''}".strip() or phone_number[:20]
        user_name = user_name[:20]
        amount_str = f"{amount_increased:,}"[:20]
        balance_str = f"{new_balance:,}"[:20]
        logger.debug(f"User name: {user_name}, Amount: {amount_str}, Balance: {balance_str}")

        api = KavenegarAPI(api_setting.api_token)
        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user_name,
            'token2': amount_str,
            'token3': balance_str,
            'type': 'sms',
        }
        logger.debug(f"Sending SMS with params: {params}")

        response = api.verify_lookup(params)
        logger.info(f"SMS sent to {phone_number}. Response: {response}")
        return True

    except APIException as e:
        logger.error(f"APIException for {phone_number}: {str(e)} - Response: {e.response.text if e.response else 'No response'}")
        return False
    except HTTPException as e:
        logger.error(f"HTTPException for {phone_number}: {str(e)} - Response: {e.response.text if e.response else 'No response'}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in send_wallet_increase_sms: {str(e)}", exc_info=True)
        return False