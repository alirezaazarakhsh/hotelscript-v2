import logging
from django.dispatch import receiver
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.db.models import Q
from authentication.models import BaseUser
from bashgah_moshtarian.models import RoomDiscountCode, ShoppingCenterDiscountCode
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

def send_discount_sms(discount_code, user=None, send_to_all=False, pattern_section='discountcode'):
    try:
        # Get SMS settings
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            logger.error("KavenegarSMSSetting not found")
            return False

        # Get SMS pattern
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            logger.error(f"SMSPattern for section '{pattern_section}' not found")
            return False

        # Determine the target name (room or shopping center)
        target_name = (discount_code.room.name if hasattr(discount_code, 'room')
                       else discount_code.shopping_center_name)

        # Initialize Kavenegar API
        api = KavenegarAPI(api_setting.api_token)

        # Handle single user or all users
        target_users = [user] if user else discount_code.users.all()
        if send_to_all and not user:
            target_users = discount_code.users.all()
        elif not target_users and user:
            target_users = [user]

        if not target_users:
            logger.error("No users specified or found in discount_code.users")
            return False

        success = False
        for target_user in target_users:
            # Prepare token values
            user_name = (discount_code.get_users_with_names()[0] if discount_code.users.filter(id=target_user.id).exists()
                         else target_user.phone_number)
            params = {
                'receptor': target_user.phone_number,
                'template': template_obj.pattern_code,
                'token': user_name,  # %token -> User name or phone number
                'token2': discount_code.code,  # %token2 -> Discount code
                'token3': discount_code.discount_value,  # %token3 -> Discount value
                'token10': target_name,  # %token10 -> Room or Shopping Center name
                'token20': (discount_code.expires_at.strftime('%Y/%m/%d') if discount_code.expires_at
                            else 'نامحدود'),  # %token20 -> Expiry date
                'type': 'sms',
            }

            try:
                # Send SMS
                response = api.verify_lookup(params)
                logger.info(f"Response from Kavenegar for {target_user.phone_number}: {response}")
                success = True
            except APIException as e:
                logger.error(f'APIException for {target_user.phone_number}: {e}')
            except HTTPException as e:
                logger.error(f'HTTPException for {target_user.phone_number}: {e}')

        return success

    except Exception as e:
        logger.error(f'Unexpected error in send_discount_sms: {e}')
        return False

# Signal to send SMS when users are added to discount code
@receiver(m2m_changed, sender=RoomDiscountCode.users.through)
@receiver(m2m_changed, sender=ShoppingCenterDiscountCode.users.through)
def send_discount_sms_on_users_added(sender, instance, action, pk_set, **kwargs):
    """
    Sends SMS to users added to a discount code's users field.
    """
    if action == 'post_add':
        users = BaseUser.objects.filter(pk__in=pk_set)
        for user in users:
            send_discount_sms(instance, user=user)