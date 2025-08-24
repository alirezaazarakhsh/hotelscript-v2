from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern
from bashgah_moshtarian.models import CustomerClubPoint

def send_customer_club_point_sms(user, added_points, pattern_section='customerclubpoint'):
    """
    افزایش امتیاز کاربر و ارسال SMS
    """
    try:
        # دریافت یا ایجاد رکورد امتیاز کاربر
        customer_points, created = CustomerClubPoint.objects.get_or_create(user=user)

        # افزایش امتیاز
        customer_points.points += added_points
        customer_points.save()

        # شماره تلفن
        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            print(f"No phone number found for user {user}")
            return False

        if phone_number.startswith("0"):
            phone_number = "98" + phone_number[1:]

        # تنظیمات Kavenegar
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("KavenegarSMSSetting not found")
            return False

        # پترن پیامک
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
            'token': user.first_name or "کاربر",
            'token2': str(added_points),
            'token3': str(customer_points.points),
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Kavenegar response:", response)
        return True

    except APIException as e:
        print(f"APIException: {e}")
    except HTTPException as e:
        print(f"HTTPException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return False




# اس ام اس دریافت هدیه ثبت‌نام برای باشگاه مشتریان
def send_registration_gift_sms(user, added_points, pattern_section='registrationgift'):
    try:
        customer_points, created = CustomerClubPoint.objects.get_or_create(user=user)
        customer_points.points += added_points
        customer_points.save()

        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            print(f"No phone number found for user {user}")
            return False

        if phone_number.startswith("0"):
            phone_number = "98" + phone_number[1:]

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

        print(f"Pattern code: {template_obj.pattern_code}")  # برای دیباگ
        api = KavenegarAPI(api_setting.api_token)

        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': str(added_points),
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Kavenegar response:", response)
        return True

    except APIException as e:
        print(f"APIException: {e}")
    except HTTPException as e:
        print(f"HTTPException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return False