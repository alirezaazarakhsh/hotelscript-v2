from rest_framework import serializers
from .models import (
    Province,
    City,
    HotelType,
    Hotel,
    Facilities,
    RoomFacilities,
    RoomService,
)

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = (
            'name',
        )

class CitySerializer(serializers.ModelSerializer):
    province = serializers.SerializerMethodField()
    class Meta:
        model = City
        fields = (
            'name',
            'province',
        )
    
    def get_province(self, obj):
        return obj.province.name

class HotelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelType
        fields = (
            'id',
            'title',
        )

class HotelListSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    type = serializers.SerializerMethodField()
    original_total_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            'name',
            'slug',
            'city',
            'address',
            'main_image',
            'stars',
            'type',
            'is_special_offer',
            'original_total_price',
            'total_price',
            'rating',
        )
    
    def get_type(self, obj):
        return obj.type.title

    def get_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('total_price')

    def get_original_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('original_total_price')
    
    def get_rating(self, obj):
        return obj.rating if obj.rating else None

class FacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facilities
        fields = (
            'id',
            'title',
        )

class RoomFacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomFacilities
        fields = (
            'id',
            'title',
        )

class RoomServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomService
        fields = (
            'id',
            'title',
        )
