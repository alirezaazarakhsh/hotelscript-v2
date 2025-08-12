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
    activated_at = serializers.SerializerMethodField()

    class Meta:
        model = DiscountActivationRecord
        fields = ['id', 'user', 'discount_type', 'code', 'activated_at', 'reward_claimed']

    def get_code(self, obj):
        code = obj.room_discount_code or obj.shopping_discount_code
        return code.code if code else '—'

    def get_activated_at(self, obj):
        return date2jalali(obj.activated_at).strftime('%Y/%m/%d')