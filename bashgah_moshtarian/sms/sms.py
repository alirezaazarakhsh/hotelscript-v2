from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern

def send_customer_club_point_sms(phone_number, user_name, added_points, total_points, pattern_section='customerclubpoint'):
    try:
        # گرفتن تنظیمات سامانه فعال
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("KavenegarSMSSetting not found")
            return False

        # پیدا کردن پترن متناسب با بخش
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()
        if not template_obj:
            print(f"SMSPattern for section '{pattern_section}' not found")
            return False

        # اصلاح فرمت شماره ایران
        if phone_number.startswith("0"):
            phone_number = "98" + phone_number[1:]

        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user_name,
            'token2': str(added_points),
            'token3': str(total_points),
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Response from Kavenegar:", response)

        return True

    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')

    return False
