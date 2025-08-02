# serializers.py

from rest_framework import serializers

from reservation.models import Room
from .models import RoomDiscountCode, ShoppingCenterDiscountCode


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
