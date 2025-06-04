from kavenegar import KavenegarAPI, APIException, HTTPException
from django.conf import settings

def send_otp_sms(phone_number, code):
    try:
        api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
        params = {
            'receptor': phone_number,
            'template': 'verifysafarnameh',  # 
            'token': code,
            'type': 'sms',  
        }
        api.verify_lookup(params)
        return True
    except APIException as e:
        print(f'APIException: {e}')
    except HTTPException as e:
        print(f'HTTPException: {e}')
    return False
