from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import RoomDiscountCode
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
        'user',
        'usage_limit',
        'required_points',
        'expires_at',
        'created_at',
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
    )
    autocomplete_fields = ('room', 'user')
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
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('room', 'user')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'room':
            kwargs['queryset'] = Room.objects.all().order_by('title')
        if db_field.name == 'user':
            kwargs['queryset'] = BaseUser.objects.all().order_by('phone_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
