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

from .serializers import (
    AuthSerializer,
    UserProfileSerializer,
    JuridicalProfileSerializer,
    JuridicalProfileDocumentSerializer,
)
from .utils import generate_otp_code, send_otp_code
from .models import (
    BaseUser,
    OTP,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
)
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import (
    RetrieveUpdateAPIView,
    GenericAPIView,
)
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
)
from .permissions import (
    IsJuridicalProfileDocumentOwner,
)

class APILogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        # if self.request.data.get('all'):
        #     token: OutstandingToken
        #     for token in OutstandingToken.objects.filter(user=request.user):
        #         _, _ = BlacklistedToken.objects.get_or_create(token=token)
        #     return Response()
        try:
            if refresh_token := self.request.data.get('refresh_token'):
                outstanding_token = RefreshToken(token=refresh_token)
                outstanding_token.blacklist()
                return Response()
            else:
                return Response(
                    {
                        "detail": "refresh_token is required"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
                return Response(
                    {
                        "detail": str(e)
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

class AuthView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        request_body=AuthSerializer
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {
                    "detail": _("you are already logged in")
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = request.data.get('phone')
        user = BaseUser.objects.get_by_phone_or_create(phone)

        try:
            last_user_otp = user.otps.latest('created')
            wait_time_seconds = -(timezone.now() - last_user_otp.expired).total_seconds()
            if wait_time_seconds >= 0:
                return Response(
                    {
                        "detail": _("wait up to %(minute)d minute to receive the verfication code again") % {'minute': wait_time_seconds // 60 + 1}
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

        return Response()

class TokenObtainPairView(JwtTokenObtainPairView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated :
            return Response(
                {
                    "detail": _("you are already logged in")
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data)

class TokenRefreshView(JwtTokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class UserProfileRetrieveUpdateView(RetrieveUpdateAPIView, CreateModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user.natural_profile
    
    def get(self, request, *args, **kwargs):
        try:
            return self.retrieve(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
            )
    
    def put(self, request, *args, **kwargs):
        request.data['base_user'] = request.user.pk
        try:
            return self.update(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return super().create(request, *args, **kwargs)

class JuridicalProfileRetrieveUpdateView(RetrieveUpdateAPIView, CreateModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = JuridicalProfileSerializer

    def get_object(self):
        return self.request.user.natural_profile.juridical_profile
    
    def get(self, request, *args, **kwargs):
        try:
            return self.retrieve(request, *args, **kwargs)
        except JuridicalProfile.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
            )
    
    def put(self, request, *args, **kwargs):
        request.data['natural_profile'] = request.user.natural_profile.pk
        request.data['status'] = 'checking'
        try:
            return self.update(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return super().create(request, *args, **kwargs)

class JuridicalProfileDocumentListCreateDestroyView(ListModelMixin,
                                                    CreateModelMixin,
                                                    DestroyModelMixin,
                                                    GenericAPIView):
    permission_classes = (
        IsAuthenticated,
        IsJuridicalProfileDocumentOwner,
    )
    serializer_class = JuridicalProfileDocumentSerializer

    def get_juridical_profile_query_set(self):
        try:
            return JuridicalProfile.objects.select_related(
                'natural_profile',
                'natural_profile__base_user',
            ).filter(natural_profile__base_user=self.request.user)
        except:
            return JuridicalProfile.objects.none()

    def get_queryset(self):
        try:
            return JuridicalProfileDocument.objects.select_related(
                'profile',
                'profile__natural_profile',
                'profile__natural_profile__base_user',
            ).filter(profile__natural_profile__base_user=self.request.user)
        except:
            return JuridicalProfileDocument.objects.none()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        request.data['profile'] = request.user.natural_profile.juridical_profile.pk
        self.get_juridical_profile_query_set().update(status='checking')
        return super().create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.get_juridical_profile_query_set().update(status='checking')
        return self.destroy(request, *args, **kwargs)
