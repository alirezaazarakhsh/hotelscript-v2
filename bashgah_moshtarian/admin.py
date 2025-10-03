from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CustomerClubPoint, DiscountActivationRecord, RoomDiscountCode, ShoppingCenterDiscountCode, HotelDiscountCode
from reservation.models import Room, Hotel
from authentication.models import BaseUser
from config.models import UserLevel


@admin.register(RoomDiscountCode)
class RoomDiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'room',
        'discount_value',
        'usage_limit',
        'remaining_uses',
        'required_points',
        'user_level',
        'expires_at',
    )
    search_fields = (
        'code',
        'room__title',
        'users__phone_number',
        'users__natural_profile__first_name',
        'users__natural_profile__last_name',
        'user_level__title',
    )
    autocomplete_fields = ('room', 'user_level')
    list_editable = (
        'discount_value',
        'usage_limit',
        'required_points',
        'user_level',
        'expires_at',
    )
    list_per_page = 25
    readonly_fields = ('created_at', 'remaining_uses')
    filter_horizontal = ('users', 'activated_users')

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('room', 'code', 'discount_value', 'users'),
            'description': _('اطلاعات اصلی کد تخفیف را وارد کنید.'),
        }),
        (_('تنظیمات استفاده'), {
            'fields': ('usage_limit', 'remaining_uses', 'required_points', 'user_level', 'expires_at'),
            'description': _('تنظیمات مربوط به محدودیت‌ها و شرایط استفاده از کد تخفیف.'),
        }),
        (_('اطلاعات تکمیلی'), {
            'fields': ('activation_rules', 'activated_users'),
            'description': _('قوانین و کاربران استفاده‌کننده کد تخفیف.'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('room', 'user_level').prefetch_related('users', 'activated_users')

    def get_users_display(self, obj):
        return ", ".join(obj.get_users_with_names())
    get_users_display.short_description = "کاربران (شماره و نام)"

    def get_activated_users_display(self, obj):
        return ", ".join(obj.get_activated_users_with_names())
    get_activated_users_display.short_description = "کاربران استفاده‌کننده (شماره و نام)"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'room':
            kwargs['queryset'] = Room.objects.all().order_by('title')
        if db_field.name == 'user_level':
            kwargs['queryset'] = UserLevel.objects.all().order_by('title')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        if db_field.name == 'activated_users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(ShoppingCenterDiscountCode)
class ShoppingCenterDiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'shopping_center_name',
        'discount_value',
        'required_points',
        'user_level',
        'expires_at',
    )
    search_fields = (
        'code',
        'shopping_center_name',
        'users__phone_number',
        'users__natural_profile__first_name',
        'users__natural_profile__last_name',
        'user_level__title',
    )
    autocomplete_fields = ('user_level',)
    list_editable = (
        'discount_value',
        'required_points',
        'user_level',
        'expires_at',
    )
    list_per_page = 25
    filter_horizontal = ('users', 'activated_users')

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': (
                'shopping_center_name',
                'shopping_center_image',
                'code',
                'discount_value',
                'users',
            ),
            'description': _('اطلاعات اصلی کد تخفیف را وارد کنید.'),
        }),
        (_('تنظیمات استفاده'), {
            'fields': (
                'required_points',
                'user_level',
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
        return super().get_queryset(request).select_related('user_level').prefetch_related('users', 'activated_users')

    def get_users_display(self, obj):
        return ", ".join(obj.get_users_with_names())
    get_users_display.short_description = "کاربران (شماره و نام)"

    def get_activated_users_display(self, obj):
        return ", ".join(obj.get_activated_users_with_names())
    get_activated_users_display.short_description = "کاربران فعال‌کننده (شماره و نام)"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_level':
            kwargs['queryset'] = UserLevel.objects.all().order_by('title')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        if db_field.name == 'activated_users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CustomerClubPoint)
class CustomerClubPointAdmin(admin.ModelAdmin):
    list_display = ('user', 'points')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__natural_profile')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(HotelDiscountCode)
class HotelDiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'hotel',
        'discount_value',
        'usage_limit',
        'remaining_uses',
        'required_points',
        'user_level',
        'expires_at',
    )
    search_fields = (
        'code',
        'hotel__name',
        'users__phone_number',
        'users__natural_profile__first_name',
        'users__natural_profile__last_name',
        'user_level__title',
    )
    autocomplete_fields = ('hotel', 'user_level')
    list_editable = (
        'discount_value',
        'usage_limit',
        'required_points',
        'user_level',
        'expires_at',
    )
    list_per_page = 25
    readonly_fields = ('created_at', 'remaining_uses')
    filter_horizontal = ('users', 'activated_users')

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('hotel', 'code', 'discount_value', 'users'),
            'description': _('اطلاعات اصلی کد تخفیف را وارد کنید.'),
        }),
        (_('تنظیمات استفاده'), {
            'fields': ('usage_limit', 'remaining_uses', 'required_points', 'user_level', 'expires_at'),
            'description': _('تنظیمات مربوط به محدودیت‌ها و شرایط استفاده از کد تخفیف.'),
        }),
        (_('اطلاعات تکمیلی'), {
            'fields': ('activation_rules', 'activated_users'),
            'description': _('قوانین و کاربران استفاده‌کننده کد تخفیف.'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hotel', 'user_level').prefetch_related('users', 'activated_users')

    def get_users_display(self, obj):
        return ", ".join(obj.get_users_with_names())
    get_users_display.short_description = "کاربران (شماره و نام)"

    def get_activated_users_display(self, obj):
        return ", ".join(obj.get_activated_users_with_names())
    get_activated_users_display.short_description = "کاربران استفاده‌کننده (شماره و نام)"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'hotel':
            kwargs['queryset'] = Hotel.objects.all().order_by('name')
        if db_field.name == 'user_level':
            kwargs['queryset'] = UserLevel.objects.all().order_by('title')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        if db_field.name == 'activated_users':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(DiscountActivationRecord)
class DiscountActivationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'user_phone_and_name',
        'discount_type',
        'get_discount_code',
        'activated_at',
        'reward_claimed',
    )
    list_filter = (
        'discount_type',
        'reward_claimed',
        'activated_at',
    )
    search_fields = (
        'user__phone_number',
        'user__natural_profile__first_name',
        'user__natural_profile__last_name',
        'room_discount_code__code',
        'shopping_discount_code__code',
        'hotel_discount_code__code',
    )
    autocomplete_fields = ('user', 'room_discount_code', 'shopping_discount_code', 'hotel_discount_code')
    list_per_page = 25
    ordering = ('-activated_at',)

    fieldsets = (
        (_('اطلاعات کاربر و کد'), {
            'fields': (
                'user',
                'discount_type',
                'room_discount_code',
                'shopping_discount_code',
                'hotel_discount_code',
            ),
            'description': _('انتخاب کاربر و کد تخفیف مربوطه'),
        }),
        (_('اطلاعات فعال‌سازی و جایزه'), {
            'fields': (
                'activated_at',
                'reward_claimed',
            ),
            'description': _('وضعیت دریافت جایزه و تاریخ فعال‌سازی'),
        }),
    )
    readonly_fields = ('activated_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user__natural_profile',
            'room_discount_code',
            'shopping_discount_code',
            'hotel_discount_code'
        )

    def user_phone_and_name(self, obj):
        if obj.user and hasattr(obj.user, 'natural_profile'):
            full_name = f"{obj.user.natural_profile.first_name or ''} {obj.user.natural_profile.last_name or ''}".strip()
            return f"{obj.user.phone_number} - {full_name}" if full_name else obj.user.phone_number
        return obj.user.phone_number if obj.user else "-"
    user_phone_and_name.short_description = _('شماره و نام کاربر')

    def get_discount_code(self, obj):
        if obj.room_discount_code:
            return obj.room_discount_code.code
        if obj.shopping_discount_code:
            return obj.shopping_discount_code.code
        if obj.hotel_discount_code:
            return obj.hotel_discount_code.code
        return "-"
    get_discount_code.short_description = _('کد تخفیف')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().select_related('natural_profile').order_by('phone_number')
        if db_field.name == 'room_discount_code':
            kwargs['queryset'] = RoomDiscountCode.objects.all().select_related('room').order_by('code')
        if db_field.name == 'shopping_discount_code':
            kwargs['queryset'] = ShoppingCenterDiscountCode.objects.all().order_by('code')
        if db_field.name == 'hotel_discount_code':
            kwargs['queryset'] = HotelDiscountCode.objects.all().select_related('hotel').order_by('code')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)