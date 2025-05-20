from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from django.contrib.auth import authenticate
from rest_framework import exceptions
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from safarname24.serializers import ErrorMessageSerializerMixin
from .validators import validate_phone_number
from .models import (
    BaseUser,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
)

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
    base_user = serializers.PrimaryKeyRelatedField(
        queryset=BaseUser.objects.all(),
        write_only=True,
    )
    phone_number = serializers.CharField(
        source='base_user.phone_number',
        required=False,
        read_only=True,
    )
    wallet_balance = serializers.CharField(
        source='base_user.wallet.balance',
        read_only=True,
    )

    class Meta:
        model = NaturalProfile
        fields = [
            'base_user',
            'phone_number',
            'first_name',
            'last_name',
            'email',
            'national_code',
            'image',
            'postal_code',
            'address',
            'wallet_balance',
        ]
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

class JuridicalProfileSerializer(serializers.ModelSerializer):
    natural_profile = serializers.PrimaryKeyRelatedField(
        queryset=NaturalProfile.objects.all(),
        write_only=True,
    )

    class Meta:
        model = JuridicalProfile
        fields = [
            'natural_profile',
            'organization_name',
            'national_id',
            'registeration_number',
            'economical_code',
            'phone_number',
            'postal_code',
            'address',
            'email',
            'image',
            'status',
            'reject_reason',
        ]
        extra_kwargs = {
            'organization_name': {
                'required': True
            },
            'national_id': {
                'required': True
            },
            'registeration_number': {
                'required': True
            },
            'economical_code': {
                'required': True,
            },
            'phone_number': {
                'required': True,
            },
            'postal_code': {
                'required': True,
            },
            'reject_reason' : {
                'read_only': True,
            },
        }

class JuridicalProfileDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuridicalProfileDocument
        fields = [
            'profile',
            'file',
        ]
        extra_kwargs = {
            'profile': {
                'write_only': True
            },
        }
