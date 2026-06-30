import traceback

from kavenegar import KavenegarAPI, APIException, HTTPException
from setting_sms.models import KavenegarSMSSetting, SMSPattern


# ارسال OTP به شماره تلفن همراه با استفاده از پترن‌های سامانه کاوه نگار
def send_otp_sms(phone_number, code, pattern_section='otp'):
    try:
        # گرفتن تنظیمات سامانه فعال
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("========== SMS ERROR ==========")
            print("KavenegarSMSSetting not found")
            print("===============================")
            return False

        # پیدا کردن پترن
        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()

        if not template_obj:
            print("========== SMS ERROR ==========")
            print(f"SMSPattern for section '{pattern_section}' not found")
            print("===============================")
            return False

        api = KavenegarAPI(api_setting.api_token)

        params = {
            "receptor": str(phone_number),
            "template": template_obj.pattern_code,
            "token": str(code),
            "type": "sms",
        }

        print("========== OTP REQUEST ==========")
        print(params)

        response = api.verify_lookup(params)

        print("========== OTP RESPONSE ==========")
        print(response)
        print("=================================")

        return True

    except APIException as e:
        print("========== APIException ==========")
        print(str(e))
        traceback.print_exc()
        print("==================================")
        return False

    except HTTPException as e:
        print("========== HTTPException ==========")
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False

    except Exception as e:
        print("========== UNKNOWN ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False


# ارسال پیامک خوش‌آمدگویی
def send_welcome_sms(phone_number, full_name, pattern_section='welcome'):
    try:
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("========== SMS ERROR ==========")
            print("KavenegarSMSSetting not found")
            print("===============================")
            return False

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()

        if not template_obj:
            print("========== SMS ERROR ==========")
            print(f"SMSPattern for section '{pattern_section}' not found")
            print("===============================")
            return False

        api = KavenegarAPI(api_setting.api_token)

        params = {
            "receptor": str(phone_number),
            "template": template_obj.pattern_code,
            "token": str(full_name),
            "type": "sms",
        }

        print("========== WELCOME REQUEST ==========")
        print(params)

        response = api.verify_lookup(params)

        print("========== WELCOME RESPONSE ==========")
        print(response)
        print("=====================================")

        return True

    except APIException as e:
        print("========== APIException ==========")
        print(str(e))
        traceback.print_exc()
        print("==================================")
        return False

    except HTTPException as e:
        print("========== HTTPException ==========")
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False

    except Exception as e:
        print("========== UNKNOWN ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False


# ارسال پیامک خروج
def send_logout_sms(phone_number, full_name, pattern_section='logout'):
    try:
        api_setting = KavenegarSMSSetting.objects.first()
        if not api_setting:
            print("========== SMS ERROR ==========")
            print("KavenegarSMSSetting not found")
            print("===============================")
            return False

        template_obj = SMSPattern.objects.filter(
            sms_setting=api_setting,
            name_fa=pattern_section
        ).first()

        if not template_obj:
            print("========== SMS ERROR ==========")
            print(f"SMSPattern for section '{pattern_section}' not found")
            print("===============================")
            return False

        api = KavenegarAPI(api_setting.api_token)

        params = {
            "receptor": str(phone_number),
            "template": template_obj.pattern_code,
            "token": str(full_name),
            "type": "sms",
        }

        print("========== LOGOUT REQUEST ==========")
        print(params)

        response = api.verify_lookup(params)

        print("========== LOGOUT RESPONSE ==========")
        print(response)
        print("====================================")

        return True

    except APIException as e:
        print("========== APIException ==========")
        print(str(e))
        traceback.print_exc()
        print("==================================")
        return False

    except HTTPException as e:
        print("========== HTTPException ==========")
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False

    except Exception as e:
        print("========== UNKNOWN ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        traceback.print_exc()
        print("===================================")
        return False