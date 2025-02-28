from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
from .models import BaseUser, OTP

class AdminAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request and request.path.startswith('/admin/'):
            try:
                username_field = BaseUser.USERNAME_FIELD
                if username:
                    user = BaseUser.objects.get(**{username_field: username})
                if user.superuser.check_password(password):
                    return user
            except BaseUser.DoesNotExist:
                return None
    
    def user_can_authenticate(self, user):
        return user.is_superuser

class UserAuthBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        try:
            phone = kwargs.get('phone')
            otp = kwargs.get('otp')
            user = BaseUser.objects.get_by_phone(phone)
            last_user_otp = user.otps.latest('created')
            is_authentecated = last_user_otp.check_code(otp) and timezone.now() <= last_user_otp.expired
            if is_authentecated:
                last_user_otp.delete()
                return user
        except BaseUser.DoesNotExist:
            return None
        except OTP.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return BaseUser.objects.get(pk=user_id)
        except BaseUser.DoesNotExist:
            return None
