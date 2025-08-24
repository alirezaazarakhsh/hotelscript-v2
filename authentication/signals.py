# اس ام اس دریافت هدیه ثبت‌نام برای باشگاه مشتریان
def send_registration_gift_sms(user, added_points, pattern_section='registrationgift'):
    """
    فقط ارسال SMS هدیه ثبت‌نام (بدون تغییر امتیاز کاربر)
    """
    try:
        # گرفتن رکورد امتیاز
        customer_points = CustomerClubPoint.objects.get(user=user)

        # شماره تلفن
        phone_number = getattr(user, 'phone_number', None)
        if not phone_number:
            print(f"No phone number found for user {user}")
            return False

        # تبدیل شماره به فرمت بین‌المللی
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

        # آماده‌سازی پارامترها
        params = {
            'receptor': phone_number,
            'template': template_obj.pattern_code,
            'token': user.first_name or "کاربر",
            'token2': str(added_points),              # امتیاز اضافه‌شده (۳۰۰)
            'token3': str(customer_points.points),    # امتیاز فعلی بعد از اضافه شدن
            'type': 'sms',
        }

        # ارسال SMS
        response = api.verify_lookup(params)
        print("Kavenegar response:", response)
        return True

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
