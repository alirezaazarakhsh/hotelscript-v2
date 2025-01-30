from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from django.contrib.auth import authenticate
from rest_framework import exceptions
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from safarname24.serializers import ErrorMessageSerializerMixin
from .validators import validate_phone_number
from django.contrib.auth import get_user_model

class UserTokenObtainPairSerializer(TokenObtainPairSerializer, ErrorMessageSerializerMixin):
    username_field = "phone"

    def __init__(self, *args, **kwargs):
        TokenObtainPairSerializer.__init__(self, *args, **kwargs)

        self.password_field = "otp"
        self.fields[self.password_field] = PasswordField()
        del self.fields["password"]

        self.fields[self.username_field].label = _('phone')
        self.fields[self.password_field].label = _('otp')

        ErrorMessageSerializerMixin.__init__(self, *args, **kwargs)
    
    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            self.password_field: attrs[self.password_field],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(
                _("validation code is not correct"),
                "no_active_account",
            )

        data = {}

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data

class AuthSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True,
                                  validators=(validate_phone_number,))

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            'phone_number',
            'first_name',
            'last_name',
            'email',
            'national_code',
            'postal_code',
            'address',
        ]
        read_only_fields = ['phone_number']
        extra_kwargs = {
            'first_name': {
                'required': True
            },
            'last_name': {
                'required': True
            },
            'national_code': {
                'required': True
            },
        }
