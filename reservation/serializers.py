from rest_framework import serializers
from .models import (
    Province,
    City,
    HotelType,
    Hotel,
    Facilities,
    RoomFacilities,
    RoomService,
    HotelTag,
    HotelFAQ,
    NearbyPlace,
    Comment,
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


class HotelTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelTag
        fields = (
            'title',
            'slug',
        )

class HotelRetrieveSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    type = serializers.SerializerMethodField()
    tags = HotelTagSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = (
            'name',
            'slug',
            'city',
            'address',
            'main_image',
            'image1',
            'image2',
            'image3',
            'image4',
            'image5',
            'image6',
            'stars',
            'type',
            'description',
            'further_description',
            'floors_count',
            'rooms_count',
            'check_in_time',
            'check_out_time',
            'latitude',
            'longitude',
            'is_special_offer',
            'rules',
            'important_notes',
            'tags',
        )
    
    def get_type(self, obj):
        return obj.type.title

class HotelFAQListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelFAQ
        fields = (
            'question',
            'answer',
        )

class NearbyPlaceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NearbyPlace
        fields = (
            'title',
            'distance',
            'driving_time',
            'walking_time',
            'image',
            'latitude',
            'longitude',
        )

class CommentListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Comment
        fields = (
            'user',
            'rating',
            'text',
            'strengths',
            'weaknesses',
            'created',
        )

    def get_user(self, obj):
        return {
            'first_name': obj.user.natural_profile.first_name,
            'last_name': obj.user.natural_profile.last_name,
            'image': obj.user.natural_profile.image if obj.user.natural_profile.image else '',
        }
