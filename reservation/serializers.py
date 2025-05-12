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
    CommentPointItem,
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

class RatingInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)

class CommentListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True)
    ratings = serializers.ListField(
        write_only=True,
        child=RatingInputSerializer(),
        help_text="""List of ratings, each item should include 'item' (comment_point_item_id) and 'rating' (1-5). Example format:
        [
            {
                "item": 1,
                "rating": 4
            },
            {
                "item": 2,
                "rating": 5
            }
        ]"""
    )

    class Meta:
        model = Comment
        fields = (
            'user',
            'rating',
            'ratings',
            'text',
            'strengths',
            'weaknesses',
            'created',
        )
        extra_kwargs = {
            'user': {
                'read_only': True,
            },
            'text': {
                'required': True,
            },
            'created': {
                'read_only': True,
            },
        }

    def get_user(self, obj):
        return {
            'first_name': obj.user.natural_profile.first_name,
            'last_name': obj.user.natural_profile.last_name,
            'image': obj.user.natural_profile.image if obj.user.natural_profile.image else '',
        }

    def validate(self, data):
        comment_point_items = CommentPointItem.objects.all()
        comment_point_items_ids = set(comment_point_items.values_list('id', flat=True))
        provided_item_ids = set([rating['item'] for rating in data['ratings']])

        missing_items = comment_point_items_ids - provided_item_ids
        if missing_items:
            raise serializers.ValidationError({
                'ratings': f'برای آیتم‌های "{", ".join(map(str, missing_items))}" امتیاز ثبت نشده است.'
            })

        extra_items = provided_item_ids - comment_point_items_ids
        if extra_items:
            raise serializers.ValidationError({
                'ratings': f'آیتم‌های "{", ".join(map(str, extra_items))}" وجود ندارند!'
            })

        return data

    def create(self, validated_data):
        validated_data.pop('ratings', None)
        return super().create(validated_data)


class RatingSummarySerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = CommentPointItem
        fields = (
            'title',
            'avg_rating',
        )
