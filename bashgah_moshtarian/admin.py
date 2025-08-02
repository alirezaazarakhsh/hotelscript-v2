from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CustomerClubPoint, DiscountActivationRecord, RoomDiscountCode, ShoppingCenterDiscountCode
from reservation.models import Room
from authentication.models import BaseUser


from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import RoomDiscountCode, ShoppingCenterDiscountCode
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
        'activated_users_count',
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
                # 'user' به صورت داینامیک اضافه می‌شود در get_fields
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

    def get_fields(self, request, obj=None):
        fields = [
            'room',
            'code',
            'discount_type',
            'discount_value',
            'is_public',
        ]
        if not obj or (obj and not obj.is_public):
            fields.append('user')

        fields += [
            'usage_limit',
            'required_points',
            'expires_at',
            'activation_rules',
            'activated_users',
        ]
        return fields

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

    def save_model(self, request, obj, form, change):
        if obj.is_public:
            obj.user = None
        super().save_model(request, obj, form, change)


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
    )
   
    search_fields = (
        'code',
        'shopping_center_name',
        'user__phone_number',
        'user__natural_profile__first_name',
        'user__natural_profile__last_name',
    )
    autocomplete_fields = ('user',)
    list_editable = (
        'discount_type',
        'discount_value',
        'is_public',
        'usage_limit',
        'required_points',
        'expires_at',
    )
    list_per_page = 25

    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': (
                'shopping_center_name',
                'shopping_center_image',
                'code',
                'discount_type',
                'discount_value',
                'is_public',
                # 'user' به صورت داینامیک اضافه می‌شود در get_fields
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
            ),
            'description': _('قوانین فعال‌سازی کد تخفیف.'),
        }),
    )

    def get_fields(self, request, obj=None):
        fields = [
            'shopping_center_name',
            'shopping_center_image',
            'code',
            'discount_type',
            'discount_value',
            'is_public',
        ]
        if not obj or (obj and not obj.is_public):
            fields.append('user')

        fields += [
            'usage_limit',
            'required_points',
            'expires_at',
            'activation_rules',
        ]
        return fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'user__natural_profile')

    def user_phone_and_name(self, obj):
        if obj.user and hasattr(obj.user, 'natural_profile'):
            full_name = f"{obj.user.natural_profile.first_name or ''} {obj.user.natural_profile.last_name or ''}".strip()
            return f"{obj.user.phone_number} - {full_name}" if full_name else obj.user.phone_number
        return obj.user.phone_number if obj.user else "-"
    user_phone_and_name.short_description = _('شماره و نام کاربر')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().order_by('phone_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.is_public:
            obj.user = None
        super().save_model(request, obj, form, change)



    
    
@admin.register(CustomerClubPoint)
class CustomerClubPointAdmin(admin.ModelAdmin):
    list_display = ['user', 'points']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['user']  
    
    
    
    
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
    )
    autocomplete_fields = ('user', 'room_discount_code', 'shopping_discount_code')
    list_per_page = 25
    ordering = ('-activated_at',)

    fieldsets = (
        (_('اطلاعات کاربر و کد'), {
            'fields': (
                'user',
                'discount_type',
                'room_discount_code',
                'shopping_discount_code',
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
        return "-"
    get_discount_code.short_description = _('کد تخفیف')
