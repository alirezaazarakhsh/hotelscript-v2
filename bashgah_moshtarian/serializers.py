# serializers.py

from rest_framework import serializers

from reservation.models import Room
from .models import RoomDiscountCode, ShoppingCenterDiscountCode


class RoomSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='hotel.name', read_only=True)  # نام هتل
    title = serializers.CharField(read_only=True)  # نام اتاق (title)

    class Meta:
        model = Room
        fields = ('id', 'title', 'hotel_name')


class RoomDiscountCodeSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)  # جایگزین نمایش فقط آیدی

    class Meta:
        model = RoomDiscountCode
        fields = '__all__'


class ShoppingCenterDiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCenterDiscountCode
        fields = '__all__'
