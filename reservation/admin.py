import logging
import re
import jdatetime
from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.db.models import Q
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _
from nested_admin import NestedModelAdmin, NestedTabularInline
from authentication.models import BaseUser
from reservation.forms import BestHotelsAdminForm, CityAdminForm, HotelAdminForm
from .models import (
    BestHotels,
    ClosedDate,
    HotelTagPublic,
    Province,
    City,
    HotelType,
    HotelTag,
    Facilities,
    ReservationApprovalDuration,
    Reservationhotel,
    RoomDatePrice,
    RoomFacilities,
    Hotel,
    HotelGallery,
    HotelGalleryImage,
    NearbyPlace,
    HotelFAQ,
    Comment,
    CommentPoint,
    CommentPointItem,
    RoomService,
    Room,
    Passenger,
    SuggestedCommentItem,
    ReservationRoom,
    ReservationRoomPassenger
)



@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug',
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    form = CityAdminForm
    list_display = (
        'id',
        'name',
        'slug',
        'image',
        'province',
        'show_in_homepage',
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(HotelType)
class HotelTypeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(HotelTag)
class HotelTagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(Facilities)
class FacilitiesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'icon_preview',
    )
    search_fields = (
        'title',
        'icon__title_icon',
    )
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


@admin.register(RoomFacilities)
class RoomFacilitiesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'icon_preview',
    )
    search_fields = (
        'title',
        'icon__title_icon',
    )
    autocomplete_fields = ('icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'title',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


class HotelTagPublicInline(admin.TabularInline):
    model = HotelTagPublic
    extra = 0  # No extra empty forms by default
    max_num = 3  # Maximum of 5 tags
    fields = ('title',)
    verbose_name = _('تگ عمومی')
    verbose_name_plural = _('تگ‌های عمومی')

# Updated HotelAdmin class
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm

    fields = (
        'name',
        'slug',
        'city',
        'best_logo',
        'logo_preview',
        'latitude',
        'longitude',
        'stars',
        'rating',
        'reservation_count',
        'type',
        'floors_count',
        'rooms_count',
        'check_in_time',
        'check_out_time',
        'has_check_in_half_day_charge',
        'has_check_out_half_day_charge',
        'tags',
        'facilities',
        'room_facilities',
        'is_special_offer',
        'is_flash_sale',
        'is_best_seller',
        'main_image',
        'image1',
        'image2',
        'image3',
        'image4',
        'address',
        'description',
        'further_description',
        'rules',
        'important_notes',
    )

    list_display = (
        'id',
        'name',
        'slug',
        'city',
        'address',
        'latitude',
        'longitude',
        'stars',
        'rating',
        'type',
        'floors_count',
        'logo_preview',
        'show_public_tags',
    )
    search_fields = (
        'name',
        'address',
        'public_tags__title',  # Enable searching by public tag titles
    )
    autocomplete_fields = ['tags', 'facilities', 'room_facilities', 'best_logo']
    readonly_fields = ('logo_preview',)
    inlines = [HotelTagPublicInline]  # Add the inline

    def logo_preview(self, obj):
        if obj.best_logo and obj.best_logo.image_logo_hotel:
            return format_html(
                '<div style="display:flex;align-items:center;">'
                '<img src="{}" width="100" height="100" style="margin-right:8px; object-fit: contain;" />'
                '</div>',
                obj.best_logo.image_logo_hotel.url
            )
        return "-"
    logo_preview.short_description = "لوگو انتخاب‌شده"

    def show_public_tags(self, obj):
        qs = obj.public_tags.all()  # Access public_tags related_name
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((tag.title,) for tag in qs)
        )
    show_public_tags.short_description = 'تگ‌های عمومی'


class HotelGalleryImageInline(admin.TabularInline):
    model = HotelGalleryImage
    extra = 1
    fields = ('image', 'order', 'preview',)
    readonly_fields = ('preview',)
    ordering = ('order',)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" style="object-fit: cover; border: 1px solid #ccc; border-radius: 4px;" />',
                obj.image.url
            )
        return "-"
    preview.short_description = 'پیش‌نمایش'


@admin.register(HotelGallery)
class HotelGalleryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'hotel')
    search_fields = ('title', 'hotel__name')
    autocomplete_fields = ['hotel']
    inlines = [HotelGalleryImageInline]


@admin.register(NearbyPlace)
class NearbyPlaceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'hotel',
        'distance',
        'driving_time',
        'walking_time',
        'latitude',
        'longitude',
    )
    search_fields = (
        'title',
    )


@admin.register(HotelFAQ)
class HotelFAQAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'question',
        'hotel',
        'icon_preview',
    )
    search_fields = (
        'question',
        'hotel__title',
        'icon__title_icon',
    )
    autocomplete_fields = ('hotel', 'icon',)
    readonly_fields = ('icon_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'question',
                'answer',
                'hotel',
                'icon',
                'icon_preview',
            )
        }),
    )

    def icon_preview(self, obj):
        if obj.icon and hasattr(obj.icon, 'svg_icon') and obj.icon.svg_icon:
            return format_html(
                '<div style="display:flex; align-items:center;">'
                '<img src="{}" width="30" height="30" style="margin-right:8px; object-fit: contain;" />'
                '<span>{}</span>'
                '</div>',
                obj.icon.svg_icon.url,
                obj.icon.title_icon
            )
        return "-"
    icon_preview.short_description = "آیکون انتخاب‌شده"


class CommentPointInline(admin.TabularInline):
    model = CommentPoint
    extra = 1
    autocomplete_fields = ['comment_point_item']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'hotel',
        'text',
        'show_strengths',
        'show_weaknesses',
        'stars',
        'is_approved',
        'created_jalali',
    )
    search_fields = (
        'text',
        'strengths__title',
        'weaknesses__title',
    )
    list_filter = (
        'is_approved',
        'stars',
    )
    autocomplete_fields = ['user', 'hotel', 'suggested_items']
    exclude = ['suggested_items']
    inlines = [CommentPointInline]

    def show_strengths(self, obj):
        qs = obj.strengths.all()
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((s.title,) for s in qs)
        )
    show_strengths.short_description = 'نقاط قوت'

    def show_weaknesses(self, obj):
        qs = obj.weaknesses.all()
        if not qs.exists():
            return "-"
        return format_html_join(
            mark_safe('<br>'),
            '{}',
            ((w.title,) for w in qs)
        )
    show_weaknesses.short_description = 'نقاط ضعف'

    def created_jalali(self, obj):
        if obj.created:
            return jdatetime.datetime.fromgregorian(datetime=obj.created).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    
    created_jalali.admin_order_field = 'created'
    created_jalali.short_description = 'تاریخ ایجاد (شمسی)'


@admin.register(CommentPointItem)
class CommentPointItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


@admin.register(SuggestedCommentItem)
class SuggestedCommentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ['title']


@admin.register(RoomService)
class RoomServiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )


class RoomDateInline(admin.TabularInline):
    model = RoomDatePrice
    extra = 1
    fields = (
        'user_level',
        'start_date',
        'end_date',
        'price',
        'extra_passenger_price',
        'discount_type',
        'discount_value',
        'discount_date',
        'is_fixed_discount_one_time',
    )
    ordering = ('start_date',)


class ClosedDateInline(admin.TabularInline):
    model = ClosedDate
    extra = 1
    fields = ('date', 'user_level')
    autocomplete_fields = ('user_level',)
    ordering = ('date',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hotel',
        'title',
        'customer_club_points',
        'inventory',
        'count',
        'auto_approved_count',
        'room_capacity',
        'extra_capacity',
    )
    search_fields = ('title',)
    autocomplete_fields = ('hotel',)
    fields = (
        'hotel',
        'title',
        'description',
        'inventory',
        'count',
        'auto_approved_count',
        'customer_club_points',
        'room_capacity',
        'extra_capacity',
        'services',
    )
    inlines = [RoomDateInline]


@admin.register(RoomDatePrice)
class RoomDatePriceAdmin(admin.ModelAdmin):
    list_display = (
        'room',
        'user_level',
        'start_date',
        'end_date',
        'price',
        'discount_type',
        'discount_value',
        'discount_date',
        'is_fixed_discount_one_time',
    )
    list_filter = (
        'room',
        'user_level',
        'discount_type',
        'is_fixed_discount_one_time',
    )
    search_fields = (
        'room__title',
        'user_level__title',
    )
    autocomplete_fields = ('room', 'user_level')
    ordering = ('room', 'start_date', 'user_level')
    fieldsets = (
        (_('اطلاعات بازه و اتاق'), {
            'fields': (
                'room',
                'user_level',
                'start_date',
                'end_date',
            )
        }),
        (_('قیمت‌گذاری'), {
            'fields': (
                'price',
                'extra_passenger_price',
            )
        }),
        (_('تخفیف'), {
            'fields': (
                'discount_type',
                'discount_value',
                'discount_date',
                'is_fixed_discount_one_time',
            )
        }),
    )
    inlines = [ClosedDateInline]


# @admin.register(ClosedDate)
# class ClosedDateAdmin(admin.ModelAdmin):
#     list_display = ('room_date', 'date', 'user_level')
#     list_filter = ('room_date', 'user_level')
#     search_fields = ('room_date__room__name',)
#     autocomplete_fields = ('room_date', 'user_level')
#     ordering = ('date',)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'first_name',
        'last_name',
        'identification_code',
        'phone_number',
    )
    search_fields = (
        'first_name',
        'last_name',
        'identification_code',
        'phone_number',
    )
    
    



@admin.register(BestHotels)
class BestHotelsAdmin(admin.ModelAdmin):
    form = BestHotelsAdminForm
    list_display = (
        'order',
        'title_logo',
        'image_logo_hotel',
    )
    search_fields = (
        'title_logo',
    )
    list_filter = (
        'order',
    )


@admin.register(ReservationApprovalDuration)
class ReservationApprovalDurationAdmin(admin.ModelAdmin):
    list_display = ('duration_minutes',)
    search_fields = ('duration_minutes',)
    fields = ('duration_minutes',)
    ordering = ('duration_minutes',)

    def has_add_permission(self, request):
        count = ReservationApprovalDuration.objects.count()
        if count >= 1:
            return False
        return True
    
    
    
    


class ReservationhotelAdminForm(ModelForm):
    class Meta:
        model = Reservationhotel
        fields = '__all__'

    def clean_check_in_date(self):
        check_in = self.cleaned_data['check_in_date']
        today_j = jdatetime.date.today()
        if check_in < today_j:
            raise forms.ValidationError("تاریخ ورود نمی‌تواند قبل از امروز باشد.")
        return check_in

    def clean_check_out_date(self):
        check_in = self.cleaned_data.get('check_in_date')
        check_out = self.cleaned_data['check_out_date']
        if check_in and check_out <= check_in:
            raise forms.ValidationError("تاریخ خروج باید بعد از تاریخ ورود باشد.")
        return check_out


# ---------------- Passenger Inline ----------------
class ReservationRoomPassengerInline(NestedTabularInline):
    model = ReservationRoomPassenger
    extra = 8  # بدون فرم خالی برای مسافران
    max_num = 8
    fields = ('passenger_type', 'first_name', 'last_name', 'mobile_number', 'national_code')
    can_delete = False
    autocomplete_fields = ()

    def get_max_num(self, request, obj=None, **kwargs):
        """حداکثر تعداد مسافران برابر با ظرفیت کل اتاق (ظرفیت اصلی + ظرفیت اضافه)"""
        if obj and hasattr(obj, 'room') and obj.room:  # بررسی وجود room
            return (obj.room.room_capacity + obj.room.extra_capacity) * obj.quantity
        return self.max_num  # بازگشت به مقدار پیش‌فرض

# ---------------- Room Inline ----------------
class ReservationRoomInline(NestedTabularInline):
    model = ReservationRoom
    extra = 3  # بدون فرم خالی برای اتاق‌ها
    max_num = 3
    fields = (
        'room',
        'price_per_night',
        'extra_passenger_price',
        'subtotal',
        'primary_passengers_count',
        'extra_passengers_count',
        'half_day_in_price',
        'half_day_out_price',
        'half_day_in_selected',
        'half_day_out_selected',
    )
    readonly_fields = (
        'primary_passengers_count',
        'extra_passengers_count',
        'half_day_in_price',
        'half_day_out_price',
    )
    show_change_link = False
    can_delete = False
    autocomplete_fields = ('room',)
    inlines = [ReservationRoomPassengerInline]

    def primary_passengers_count(self, obj):
        return obj.primary_passengers_count
    primary_passengers_count.short_description = _('تعداد نفر اصلی')

    def extra_passengers_count(self, obj):
        return obj.extra_passengers_count
    extra_passengers_count.short_description = _('تعداد نفر اضافه')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # اختیاری کردن فیلد room در فرم ادمین
        formset.form.base_fields['room'].required = False
        return formset

# ---------------- Reservationhotel Admin ----------------
@admin.register(Reservationhotel)
class ReservationhotelAdmin(NestedModelAdmin):
    form = ReservationhotelAdminForm
    list_display = (
        'tracking_code', 'buyer', 'reserver_first_name', 'reserver_last_name',
        'reserver_phone_number', 'check_in_date', 'check_out_date',
        'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'total_price', 'total_extra_passenger_charge', 'half_day_in_charge', 
        'half_day_out_charge', 'total_half_day_charge', 'discount', 'final_price', 
        'status', 'created_jalali', 'updated_jalali'
    )
    
    search_fields = (
        'tracking_code', 'buyer__phone_number', 'reserver_first_name',
        'reserver_last_name', 'reserver_phone_number', 'reserver_national_code'
    )
    
    list_filter = ('status', 'check_in_date', 'check_out_date')
    autocomplete_fields = ('buyer',)
    inlines = [ReservationRoomInline]

    readonly_fields = (
        'tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
        'created_jalali', 'updated_jalali',
        'total_price', 'total_extra_passenger_charge', 'half_day_in_charge', 
        'half_day_out_charge', 'total_half_day_charge', 'final_price'
    )

    fieldsets = (
        (_('اطلاعات رزرو کننده'), {
            'fields': (
                'buyer', 'reserver_first_name', 'reserver_last_name',
                'reserver_phone_number', 'reserver_national_code', 'additional_notes'
            )
        }),
        (_('تاریخ رزرو'), {
            'fields': ('check_in_date', 'check_out_date')
        }),
        (_('قیمت و وضعیت'), {
            'fields': (
                'total_price', 'total_extra_passenger_charge', 'half_day_in_charge', 
                'half_day_out_charge', 'total_half_day_charge', 'discount', 'final_price', 
                'status'
            )
        }),
        (_('اطلاعات سیستم'), {
            'fields': ('tracking_code', 'nights_count_fa', 'total_rooms_fa', 'total_guests_fa',
                       'created_jalali', 'updated_jalali')
        }),
    )

    # ---------------- Jalali Dates ----------------
    @admin.display(description=_('تاریخ ایجاد (شمسی)'))
    def created_jalali(self, obj):
        if obj.created_at:
            dt = obj.created_at.togregorian() if hasattr(obj.created_at, 'togregorian') else obj.created_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'

    @admin.display(description=_('تاریخ به‌روزرسانی (شمسی)'))
    def updated_jalali(self, obj):
        if obj.updated_at:
            dt = obj.updated_at.togregorian() if hasattr(obj.updated_at, 'togregorian') else obj.updated_at
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'

    # ---------------- Counts ----------------
    @admin.display(description=_('تعداد شب‌ها'))
    def nights_count_fa(self, obj):
        return obj.nights_count if obj.pk else 0

    @admin.display(description=_('کل اتاق‌ها'))
    def total_rooms_fa(self, obj):
        return obj.total_rooms if obj.pk else 0

    @admin.display(description=_('کل مهمان‌ها'))
    def total_guests_fa(self, obj):
        return obj.total_guests if obj.pk else 0

    # ---------------- Save Model ----------------
    def save_model(self, request, obj, form, change):
        """فقط ذخیره رزرو، بدون محاسبه قیمت (چون inlines هنوز ذخیره نشدن)"""
        super().save_model(request, obj, form, change)

    # ---------------- Save Related ----------------
    def save_related(self, request, form, formsets, change):
        """بعد از ذخیره شدن inlines، قیمت‌ها محاسبه و آپدیت میشن"""
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.reservation_rooms.exists():  # فقط اگر اتاقی وجود داشته باشد
            total_price, total_extra, total_discount, half_day_in_charge, half_day_out_charge, total_half_day_charge, final_price = obj.calculate_total_price()
            obj.total_price = total_price
            obj.total_extra_passenger_charge = total_extra
            obj.discount = total_discount
            obj.half_day_in_charge = half_day_in_charge
            obj.half_day_out_charge = half_day_out_charge
            obj.total_half_day_charge = total_half_day_charge
            obj.final_price = final_price
            obj.save(update_fields=[
                'total_price', 'total_extra_passenger_charge', 'discount', 
                'half_day_in_charge', 'half_day_out_charge', 'total_half_day_charge', 
                'final_price'
            ])