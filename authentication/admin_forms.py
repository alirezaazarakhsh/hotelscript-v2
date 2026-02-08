from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate

class AdminOTPAuthenticationForm(AdminAuthenticationForm):
    """Admin login form with phone number, password, and OTP code"""
    
    username = forms.CharField(
        label="شماره تلفن",
        max_length=11,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': '09123456789'
        })
    )
    
    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور'
        })
    )
    
    otp_token = forms.CharField(
        label="کد احراز هویت",
        max_length=6,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'maxlength': '6'
        }),
        help_text='کد TOTP یا توکن ثابت 6 رقمی را وارد کنید (اگر فعال باشد)'
    )
    
    def clean(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
        
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        otp_token = self.cleaned_data.get('otp_token')
        
        if username and password:
            # First authenticate with username/password
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            
            # Check if user has TOTP device or Static tokens
            from authentication.models import BaseUser
            try:
                user = BaseUser.objects.get(phone_number=username)
                totp_devices = TOTPDevice.objects.filter(user=user, confirmed=True)
                static_devices = StaticDevice.objects.filter(user=user, confirmed=True)
                
                # بررسی وجود TOTP یا Static Device
                if totp_devices.exists() or static_devices.exists():
                    # اگر هر کدام فعال است، کد الزامی است
                    if not otp_token:
                        raise forms.ValidationError("کد احراز هویت الزامی است")
                    
                    # ابتدا TOTP را امتحان کن
                    if totp_devices.exists():
                        device = totp_devices.first()
                        
                        # Debug: print device info
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Device TOTP: {device.name}, Key: {device.key}, Token: {otp_token}")
                        
                        # Verify token (try with drift tolerance)
                        is_valid = device.verify_token(otp_token)
                        logger.warning(f"TOTP Token valid: {is_valid}")
                        
                        if is_valid:
                            self.user_cache.otp_device = device
                            return self.cleaned_data
                    
                    # اگر TOTP موفق نبود، Static Token را بررسی کن
                    if static_devices.exists():
                        device = static_devices.first()
                        try:
                            token_obj = StaticToken.objects.get(device=device, token=otp_token)
                            
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Static Token verified for user: {username}")
                            
                            # توکن استاتیک معتبر است - استفاده شد
                            token_obj.delete()
                            self.user_cache.otp_device = device
                            return self.cleaned_data
                        except StaticToken.DoesNotExist:
                            pass
                    
                    # اگر هیچ کدام موفق نبود
                    raise forms.ValidationError("کد احراز هویت نادرست است")
            except BaseUser.DoesNotExist:
                pass
        
        return self.cleaned_data
