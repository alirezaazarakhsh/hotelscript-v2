from venv import logger
from rest_framework import serializers
from reservation.models import Room, Hotel
from .models import CustomerClubPoint, DiscountActivationRecord, RoomDiscountCode, ShoppingCenterDiscountCode, HotelDiscountCode
from jalali_date import datetime2jalali


class RoomSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='hotel.name', read_only=True)  # نام هتل
    title = serializers.CharField(read_only=True)  # نام اتاق (title)
    hotel_main_image = serializers.SerializerMethodField(read_only=True)  # تصویر اصلی هتل

    class Meta:
        model = Room
        fields = ('id', 'title', 'hotel_name', 'hotel_main_image')
        ref_name = "BashgahRoomSerializer"  

    def get_hotel_main_image(self, obj):
        request = self.context.get('request')
        image = obj.hotel.main_image.url if obj.hotel and obj.hotel.main_image else None
        if image and request is not None:
            return request.build_absolute_uri(image)
        return image


class HotelSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='name', read_only=True)  # نام هتل
    main_image = serializers.SerializerMethodField(read_only=True)  # تصویر اصلی هتل

    class Meta:
        model = Hotel
        fields = ('id', 'hotel_name', 'main_image')
        ref_name = "BashgahHotelSerializer"

    def get_main_image(self, obj):
        request = self.context.get('request')
        image = obj.main_image.url if obj.main_image else None
        if image and request is not None:
            return request.build_absolute_uri(image)
        return image


class RoomDiscountCodeSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)  # جایگزین نمایش فقط آیدی
    discount_type = serializers.SerializerMethodField()
    user_level = serializers.StringRelatedField(read_only=True, allow_null=True)  # نمایش نام سطح کاربری به جای آیدی

    class Meta:
        model = RoomDiscountCode
        fields = ['id', 'discount_type', 'room', 'discount_value', 'code', 'usage_limit', 'remaining_uses', 'required_points', 'user_level', 'created_at', 'expires_at', 'activation_rules']

    def get_discount_type(self, obj):
        return 'room'


class HotelDiscountCodeSerializer(serializers.ModelSerializer):
    hotel = HotelSerializer(read_only=True)  # جایگزین نمایش فقط آیدی
    discount_type = serializers.SerializerMethodField()
    user_level = serializers.StringRelatedField(read_only=True, allow_null=True)  # نمایش نام سطح کاربری به جای آیدی

    class Meta:
        model = HotelDiscountCode
        fields = ['id', 'discount_type', 'hotel', 'discount_value', 'code', 'usage_limit', 'remaining_uses', 'required_points', 'user_level', 'created_at', 'expires_at', 'activation_rules']

    def get_discount_type(self, obj):
        return 'hotel'


class ShoppingCenterDiscountCodeSerializer(serializers.ModelSerializer):
    user_level = serializers.StringRelatedField(read_only=True, allow_null=True)  # نمایش نام سطح کاربری به جای آیدی

    class Meta:
        model = ShoppingCenterDiscountCode
        fields = '__all__'


class CustomerClubPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerClubPoint
        fields = ['points']



class DiscountActivationRecordSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    discount_type = serializers.CharField(source='get_discount_type_display', read_only=True)
    code = serializers.SerializerMethodField()
    discount_value = serializers.SerializerMethodField()
    related_info = serializers.SerializerMethodField()
    required_points = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()

    class Meta:
        model = DiscountActivationRecord
        fields = [
            'id', 'user', 'discount_type', 'code', 'discount_value',
            'required_points', 'activated_at', 'expires_at',
            'reward_claimed', 'related_info'
        ]

    def get_code(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code or obj.hotel_discount_code
        return code.code if code else '—'

    def get_discount_value(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code or obj.hotel_discount_code
        if code and hasattr(code, 'discount_value') and code.discount_value is not None:
            try:
                # برای HotelDiscountCode و RoomDiscountCode (DecimalField)
                if hasattr(code, 'discount_value') and isinstance(code.discount_value, (int, float)):
                    return f"{int(code.discount_value):,}"
                # برای ShoppingCenterDiscountCode (CharField)
                return f"{int(code.discount_value):,}"
            except (ValueError, TypeError):
                return str(code.discount_value)
        return '—'

    def get_required_points(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code or obj.hotel_discount_code
        return code.required_points if code and hasattr(code, 'required_points') else 0

    def get_expires_at(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code or obj.hotel_discount_code
        if not code or not hasattr(code, 'expires_at') or not code.expires_at:
            return None
        try:
            return code.expires_at.strftime('%Y/%m/%d')
        except (AttributeError, ValueError):
            return str(code.expires_at)

    def get_related_info(self, obj):
        try:
            if obj.discount_type == 'room' and obj.room_discount_code and obj.room_discount_code.room:
                room = obj.room_discount_code.room
                room_parts = str(room).split(" - ")
                room_type = room_parts[0].strip() if room_parts else "نامشخص"
                hotel_name = room_parts[1].strip() if len(room_parts) > 1 else "نامشخص"
                return {
                    'room_id': room.id,
                    'room_name': f"هتل {hotel_name} - اتاق {room_type}"
                }

            elif obj.discount_type == 'shopping_center' and obj.shopping_discount_code:
                # مستقیم از shopping_center_name استفاده کن
                name = getattr(obj.shopping_discount_code, 'shopping_center_name', "مرکز خرید نامشخص")
                return {
                    'shopping_center_name': name or "مرکز خرید نامشخص"
                }

            elif obj.discount_type == 'hotel' and obj.hotel_discount_code and obj.hotel_discount_code.hotel:
                hotel = obj.hotel_discount_code.hotel
                return {
                    'hotel_id': hotel.id,
                    'hotel_name': getattr(hotel, 'name', "هتل نامشخص")
                }

        except Exception as e:
            logger.warning(f"Error in get_related_info for record {obj.id}: {e}")
            pass

        return {}