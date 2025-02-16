from django.contrib import admin
from .models import User, OTP
from .forms import UserForm

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserForm
    list_display = (
        'id',
        'first_name',
        'last_name',
        'password',
        'email',
        'phone_number',
        'national_code',
        'postal_code',
        'address',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'is_active',
        'is_staff',
    )
    search_fields = (
        'phone_number',
        'national_code',
        'first_name',
        'last_name',
    )
    ordering = (
        '-id',
    )

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
