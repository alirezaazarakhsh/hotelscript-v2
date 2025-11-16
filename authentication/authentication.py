from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication class that reads the access token from cookies
    instead of the Authorization header.
    """
    
    def authenticate(self, request):
        # ابتدا سعی می‌کنیم توکن را از کوکی بخوانیم
        access_token = request.COOKIES.get('access_token')
        
        if access_token is None:
            # اگر توکن در کوکی نبود، از روش پیش‌فرض (Authorization header) استفاده می‌کنیم
            return super().authenticate(request)
        
        # اعتبارسنجی توکن
        validated_token = self.get_validated_token(access_token)
        
        # دریافت کاربر از توکن
        return self.get_user(validated_token), validated_token
