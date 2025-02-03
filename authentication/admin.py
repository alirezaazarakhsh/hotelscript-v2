from django.contrib import admin
from .models import User, OTP

# Register your models here.
@admin.register(User)
class NotifierAdmin(admin.ModelAdmin):
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

    def __str__(self):
        return "کاربران"

    def __repr__(self):
        return "کاربران"

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

@admin.register(OTP)
class NotifierAdmin(admin.ModelAdmin):
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

    def __str__(self):
        return "رمزهای یک بار مصرف"

    def __repr__(self):
        return "رمزهای یک بار مصرف"

    class Meta:
        verbose_name = "رمز یک بار مصرف"
        verbose_name_plural = "رمزهای یک بار مصرف"
