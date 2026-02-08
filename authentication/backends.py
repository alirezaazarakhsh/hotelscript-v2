from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
import jdatetime
from .models import BaseUser, OTP

class AdminAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            username_field = BaseUser.USERNAME_FIELD
            if username and password:
                user = BaseUser.objects.get(**{username_field: username})

                # بررسی وجود password و is_staff (ادمین معمولی یا سوپر یوزر)
                if user.is_staff and user.password:
                    if user.check_password(password):
                        return user
        except BaseUser.DoesNotExist:
            return None
    
    def user_can_authenticate(self, user):
        # هر کسی که is_staff باشد (ادمین معمولی یا سوپر یوزر) می‌تواند authenticate شود
        return user.is_staff
    
    def has_perm(self, user_obj, perm, obj=None):
        """
        چک کردن دسترسی‌ها:
        - سوپر یوزر: دسترسی کامل
        - ادمین معمولی: فقط دسترسی‌های گروه‌ها
        """
        if not user_obj.is_active or not user_obj.is_staff:
            return False
        if user_obj.is_superuser:
            return True
        # برای ادمین معمولی، از گروه‌ها و دسترسی‌های مستقیم استفاده می‌شود
        return super().has_perm(user_obj, perm, obj)
    
    def has_module_perms(self, user_obj, app_label):
        """
        چک کردن دسترسی به یک app:
        - سوپر یوزر: دسترسی به همه app‌ها
        - ادمین معمولی: فقط app‌هایی که در گروه‌هایش permission دارد
        """
        if not user_obj.is_active or not user_obj.is_staff:
            return False
        if user_obj.is_superuser:
            return True
        # برای ادمین معمولی، چک می‌کنیم آیا حداقل یک permission از این app دارد
        return super().has_module_perms(user_obj, app_label)

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