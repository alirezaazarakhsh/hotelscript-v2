from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
import jdatetime
from .models import BaseUser, OTP

class AdminAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request and request.path.startswith('/admin/'):
            try:
                username_field = BaseUser.USERNAME_FIELD
                if username:
                    user = BaseUser.objects.get(**{username_field: username})

                    # بررسی وجود superuser و پسورد معتبر
                    if hasattr(user, 'superuser') and user.superuser.password:
                        if user.superuser.check_password(password):
                            return user
            except BaseUser.DoesNotExist:
                return None

class UserAuthBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        try:
            phone = kwargs.get('phone')
            otp = kwargs.get('otp')
            if not phone or not otp:
                return None
            user = BaseUser.objects.get(phone_number=phone)
            last_user_otp = user.otps.latest('created')  # اصلاح از opts به otps
            is_authenticated = last_user_otp.check_code(otp) and timezone.now() <= last_user_otp.expired
            if is_authenticated:
                user.last_login = jdatetime.datetime.now()
                user.save()
                last_user_otp.delete()
                return user
        except (BaseUser.DoesNotExist, OTP.DoesNotExist):
            return None
        except Exception:  # مدیریت خطاهای غیرمنتظره
            return None

    def get_user(self, user_id):
        try:
            return BaseUser.objects.get(pk=user_id)
        except BaseUser.DoesNotExist:
            return None