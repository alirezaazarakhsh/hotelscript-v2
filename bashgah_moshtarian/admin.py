from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CustomerClubPoint, RoomDiscountCode, ShoppingCenterDiscountCode
from reservation.models import Room
from authentication.models import BaseUser


@admin.register(RoomDiscountCode)
class RoomDiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'room',
        'discount_type',
        'discount_value',
        'is_public',
        'user_phone_and_name',
        'usage_limit',
        'required_points',
        'expires_at',
        'created_at',
        'activated_users_count',
    )
    list_filter = (
        'discount_type',
        'is_public',
        'room',
        'expires_at',
    )
    search_fields = (
        'code',
        'room__title',
        'user__phone_number',
        'user__natural_profile__first_name',
        'user__natural_profile__last_name',
    )
    autocomplete_fields = ('room', 'user', 'activated_users')
    list_editable = (
        'discount_type',
        'discount_value',
        'is_public',
        'usage_limit',
        'required_points',
        'expires_at',
    )
    list_per_page = 25
    readonly_fields = ('created_at',)
    filter_horizontal = ('activated_users',)

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': (
                'room',
                'code',
                'discount_type',
                'discount_value',
                'is_public',
                'user',
            ),
            'description': _('اطلاعات اصلی کد تخفیف را وارد کنید.'),
        }),
        (_('تنظیمات استفاده'), {
            'fields': (
                'usage_limit',
                'required_points',
                'expires_at',
            ),
            'description': _('تنظیمات مربوط به محدودیت‌ها و شرایط استفاده از کد تخفیف.'),
        }),
        (_('اطلاعات تکمیلی'), {
            'fields': (
                'activation_rules',
                'activated_users',
            ),
            'description': _('قوانین و کاربران فعال‌کننده کد تخفیف.'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('room', 'user', 'user__natural_profile').prefetch_related('activated_users')

    def user_phone_and_name(self, obj):
        if obj.user and hasattr(obj.user, 'natural_profile'):
            full_name = f"{obj.user.natural_profile.first_name or ''} {obj.user.natural_profile.last_name or ''}".strip()
            return f"{obj.user.phone_number} - {full_name}" if full_name else obj.user.phone_number
        return obj.user.phone_number if obj.user else "-"
    user_phone_and_name.short_description = _('شماره و نام کاربر')

    def activated_users_count(self, obj):
        return obj.activated_users.count()
    activated_users_count.short_description = _('تعداد فعال‌کنندگان')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'room':
            kwargs['queryset'] = Room.objects.all().order_by('title')
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().order_by('phone_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)




@admin.register(ShoppingCenterDiscountCode)
class ShoppingCenterDiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'shopping_center_name',
        'discount_type',
        'discount_value',
        'is_public',
        'user_phone_and_name',
        'usage_limit',
        'required_points',
        'expires_at',
        'created_at',
        'activated_users_count',
    )
    list_filter = (
        'discount_type',
        'is_public',
        'shopping_center_name',
        'expires_at',
    )
    search_fields = (
        'code',
        'shopping_center_name',
        'user__phone_number',
        'user__natural_profile__first_name',
        'user__natural_profile__last_name',
    )
    autocomplete_fields = ('user', 'activated_users')
    list_editable = (
        'discount_type',
        'discount_value',
        'is_public',
        'usage_limit',
        'required_points',
        'expires_at',
    )
    list_per_page = 25
    readonly_fields = ('created_at',)
    filter_horizontal = ('activated_users',)

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': (
                'shopping_center_name',
                'shopping_center_image',
                'code',
                'discount_type',
                'discount_value',
                'is_public',
                'user',
            ),
            'description': _('اطلاعات اصلی کد تخفیف را وارد کنید.'),
        }),
        (_('تنظیمات استفاده'), {
            'fields': (
                'usage_limit',
                'required_points',
                'expires_at',
            ),
            'description': _('تنظیمات مربوط به محدودیت‌ها و شرایط استفاده از کد تخفیف.'),
        }),
        (_('اطلاعات تکمیلی'), {
            'fields': (
                'activation_rules',
                'activated_users',
            ),
            'description': _('قوانین و کاربران فعال‌کننده کد تخفیف.'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'user__natural_profile').prefetch_related('activated_users')

    def user_phone_and_name(self, obj):
        if obj.user and hasattr(obj.user, 'natural_profile'):
            full_name = f"{obj.user.natural_profile.first_name or ''} {obj.user.natural_profile.last_name or ''}".strip()
            return f"{obj.user.phone_number} - {full_name}" if full_name else obj.user.phone_number
        return obj.user.phone_number if obj.user else "-"
    user_phone_and_name.short_description = _('شماره و نام کاربر')

    def activated_users_count(self, obj):
        return obj.activated_users.count()
    activated_users_count.short_description = _('تعداد فعال‌کنندگان')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().order_by('phone_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)




    
    
@admin.register(CustomerClubPoint)
class CustomerClubPointAdmin(admin.ModelAdmin):
    list_display = ['user', 'points']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['user']  