from django.contrib import admin
from .models import (
    BaseUser,
    Admin,
    SuperUser,
    NaturalProfile,
    JuridicalProfile,
    OTP,
)
from .forms import (
    AdminForm,
    NaturalProfileForm,
)

# # Register your models here.
@admin.register(BaseUser)
class BaseUserAdmin(admin.ModelAdmin):
    exclude = (
        'is_superuser',
    )
    list_display = (
        'id',
        'phone_number',
        'date_joined',
    )
    search_fields = (
        'phone_number',
    )
    ordering = (
        '-id',
    )

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    form = AdminForm
    list_display = (
        'id',
        'base_user__phone_number',
        'first_name',
        'last_name',
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
    )
    ordering = (
        '-id',
    )

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

@admin.register(SuperUser)
class SuperUserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'base_user__phone_number',
    )
    search_fields = (
        'base_user__phone_number',
    )
    ordering = (
        '-id',
    )

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

@admin.register(NaturalProfile)
class NaturalProfileAdmin(admin.ModelAdmin):
    form = NaturalProfileForm
    list_display = (
        'id',
        'base_user__phone_number',
        'first_name',
        'last_name',
        'email',
        'national_code',
    )
    search_fields = (
        'base_user__phone_number',
        'first_name',
        'last_name',
        'email',
        'national_code',
    )
    ordering = (
        '-id',
    )

    def base_user__phone_number(self, obj):
        return obj.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

@admin.register(JuridicalProfile)
class JuridicalProfileAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'base_user__phone_number',
        'natural_profile__first_name',
        'natural_profile__last_name',
        'organization_name',
        'national_id',
        'registeration_number',
        'economical_code',
        'phone_number',
        'email',
        'status',
    )
    search_fields = (
        'base_user__phone_number',
        'natural_profile__first_name',
        'natural_profile__last_name',
        'organization_name',
        'national_id',
        'registeration_number',
        'economical_code',
        'phone_number',
    )
    list_filter = (
        'status',
    )
    ordering = (
        '-id',
    )

    def base_user__phone_number(self, obj):
        return obj.natural_profile.base_user.phone_number
    base_user__phone_number.short_description = 'موبایل'

    def natural_profile__first_name(self, obj):
        return obj.natural_profile.first_name
    base_user__phone_number.short_description = 'نام'

    def natural_profile__last_name(self, obj):
        return obj.natural_profile.last_name
    base_user__phone_number.short_description = 'نام خانوادگی'

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'code',
        'created',
    )
    search_fields = (
        'user',
    )
    ordering = (
        '-id',
    )
