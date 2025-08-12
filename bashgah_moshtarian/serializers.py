# serializers.py

from rest_framework import serializers

from reservation.models import Room
from .models import CustomerClubPoint, DiscountActivationRecord, RoomDiscountCode, ShoppingCenterDiscountCode
from jalali_date import datetime2jalali


class RoomSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='hotel.name', read_only=True)  # نام هتل
    title = serializers.CharField(read_only=True)  # نام اتاق (title)
    hotel_main_image = serializers.SerializerMethodField(read_only=True)  # تصویر اصلی هتل

    class Meta:
        model = Room
        fields = ('id', 'title', 'hotel_name', 'hotel_main_image')

    def get_hotel_main_image(self, obj):
        request = self.context.get('request')
        image = obj.hotel.main_image.url if obj.hotel and obj.hotel.main_image else None
        if image and request is not None:
            return request.build_absolute_uri(image)
        return image



class RoomDiscountCodeSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)  # جایگزین نمایش فقط آیدی

    class Meta:
        model = RoomDiscountCode
        fields = '__all__'


class ShoppingCenterDiscountCodeSerializer(serializers.ModelSerializer):
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
    related_info = serializers.SerializerMethodField()

    class Meta:
        model = DiscountActivationRecord
        fields = ['id', 'user', 'discount_type', 'code', 'activated_at', 'reward_claimed', 'related_info']

    def get_code(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code
        return code.code if code else '—'

    def get_related_info(self, obj):
        if obj.discount_type == 'room' and obj.room_discount_code:
            room = obj.room_discount_code.room
            room_parts = str(room).split(" - ")
            room_type = room_parts[0] if room_parts else "تویین 2"  # اسم اتاق (مثل تویین 2)
            hotel_name = room_parts[1] if len(room_parts) > 1 else "پارسیان آزادی"  # اسم هتل (مثل پارسیان آزادی)
            return {
                'room_id': room.id,
                'room_name': f"هتل {hotel_name} - اتاق {room_type}"
            }
        elif obj.discount_type == 'shopping_center' and obj.shopping_discount_code:
            shopping_center = obj.shopping_discount_code.shopping_center
            return {
                'shopping_center_id': shopping_center.id,
                'shopping_center_name': str(shopping_center)
            }
        return None