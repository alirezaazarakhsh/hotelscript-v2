# serializers.py

from rest_framework import serializers
from .models import RoomDiscountCode, ShoppingCenterDiscountCode


class RoomDiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDiscountCode
        fields = '__all__'

class ShoppingCenterDiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCenterDiscountCode
        fields = '__all__'
