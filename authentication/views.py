from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView as JwtTokenObtainPairView,
    TokenRefreshView as JwtTokenRefreshView,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .serializers import AuthSerializer
from .utils import generate_otp_code, send_otp_code
from .models import User, OTP

class APILogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        # if self.request.data.get('all'):
        #     token: OutstandingToken
        #     for token in OutstandingToken.objects.filter(user=request.user):
        #         _, _ = BlacklistedToken.objects.get_or_create(token=token)
        #     return Response({
        #         "data": None,
        #         "message": "",
        #     })
        if refresh_token := self.request.data.get('refresh_token'):
            outstanding_token = RefreshToken(token=refresh_token)
            outstanding_token.blacklist()
            return Response({
                "data": None,
                "message": "",
            })
        else:
            return Response(
                {
                    "message": "refresh_token is required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

class AuthView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        if request.user.is_authenticated :
            return Response(
                {
                    "message": _("you are already logged in")
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = request.data.get('phone')
        user = User.objects.get_by_phone_or_create(phone)

        try:
            last_user_otp = user.otps.latest('created')
            wait_time_seconds = -(timezone.now() - last_user_otp.expired).total_seconds()
            if wait_time_seconds >= 0:
                return Response(
                    {
                        "message": _("wait up to %(minute)d minute to receive the verfication code again") % {'minute': wait_time_seconds // 60 + 1}
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except OTP.DoesNotExist:
            pass
        
        code = generate_otp_code()
        otp = OTP(user=user)
        otp.set_code(code)
        otp.save()
        send_otp_code(code, phone)

        return Response({
            "data": None,
            "message": "",
        })

class TokenObtainPairView(JwtTokenObtainPairView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated :
            return Response(
                {
                    "message": _("you are already logged in")
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(
            {
                "data": serializer.validated_data,
                "message": "",
            },
            status=status.HTTP_200_OK
        )

class TokenRefreshView(JwtTokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(
            {
                "data": serializer.validated_data,
                "message": "",
            },
            status=status.HTTP_200_OK
        )
