# test_kavenegar_sms.py
from kavenegar import KavenegarAPI, APIException, HTTPException

# ---------- تنظیمات ----------
API_TOKEN = "535A305643614E3255553170724B74515547334361486549556765333651725942626B77496869555735303D"

PHONE_NUMBER = "989120759419"       
PATTERN_CODE = "plusdisscount"   
USER_NAME = "علی"                        # نام کاربر
ADDED_POINTS = 50                        # تعداد امتیاز اضافه شده
TOTAL_POINTS = 150                        # موجودی کل امتیاز کاربر
# -------------------------------

def send_customer_club_point_sms():
    try:
        api = KavenegarAPI(API_TOKEN)

        # اطمینان از فرمت شماره ایران
        phone = PHONE_NUMBER
        if phone.startswith("0"):
            phone = "98" + phone[1:]

        params = {
            'receptor': phone,
            'template': PATTERN_CODE,
            'token': USER_NAME,
            'token2': str(ADDED_POINTS),
            'token3': str(TOTAL_POINTS),
            'type': 'sms',
        }

        response = api.verify_lookup(params)
        print("Kavenegar response:", response)
        return True

    except APIException as e:
        print("APIException:", e)
    except HTTPException as e:
        print("HTTPException:", e)
    except Exception as e:
        print("Unexpected error:", e)

    return False

if __name__ == "__main__":
    if send_customer_club_point_sms():
        print("SMS sent successfully!")
    else:
        print("Failed to send SMS.")