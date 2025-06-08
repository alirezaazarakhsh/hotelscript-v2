from rest_framework import serializers
from .models import (
    BestHotels,
    ClosedDate,
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
    Room,
    RoomDate,
    Passenger,
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
            'image',
            'province',
            'show_in_homepage',
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
            'is_flash_sale',
            'is_best_seller',
            'original_total_price',
            'total_price',
            'rating',
        )

    def get_type(self, obj):
        # فرض می‌کنیم مدل HotelType فیلد title دارد
        return obj.type.title if obj.type else None

    def get_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('total_price', None)

    def get_original_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('original_total_price', None)

    def get_rating(self, obj):
        # اگر rating در مدل نیست، مقدار None می‌دهیم یا اگر می‌خواهید می‌توانید اینجا لاجیک بگذارید
        return getattr(obj, 'rating', None)



class FavoriteHotelSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    min_price = serializers.SerializerMethodField()
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
            'is_special_offer',
            'is_flash_sale',
            'is_best_seller',
            'min_price',
            'rating',
        )

    def get_min_price(self, obj):
        return obj.min_price if obj.min_price else None
    
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
        )



class HotelImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = (
            'main_image',
            'image1',
            'image2',
            'image3',
            'image4',
        )


class HotelDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ('description',)



class HotelIntroductionSerializer(serializers.ModelSerializer):
    logo_preview = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            'name',
            'latitude',
            'longitude',
            'best_logo',
            'logo_preview',
            'stars',
            'address',
            'floors_count',
            'rooms_count',
            'check_in_time',
            'check_out_time',
        )

    def get_logo_preview(self, obj):
        if obj.best_logo and obj.best_logo.image_logo_hotel:
            return obj.best_logo.image_logo_hotel.url
        return None


class HotelFurtherDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ('further_description',)



class HotelRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = (
            'rules',
            'important_notes',
        )

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

class RoomListSerializer(serializers.ModelSerializer):
    original_total_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    services = RoomServiceSerializer(many=True)

    class Meta:
        model = Room
        fields = (
            'id',
            'title',
            'description',
            'capacity',
            'extra_capacity',
            'customer_club_points',
            'services',
            'total_price',
            'original_total_price',
        )
    
    def get_total_price(self, obj):
        return self.context.get('room_data_map', {}).get(obj.id, {}).get('total_price')
    
    def get_original_total_price(self, obj):
        return self.context.get('room_data_map', {}).get(obj.id, {}).get('original_total_price')

class RoomDateListSerializer(serializers.ModelSerializer):
    jalali_date = serializers.SerializerMethodField()
    jalali_dateend = serializers.SerializerMethodField()
    discounted_price = serializers.IntegerField(read_only=True)
    original_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = RoomDate
        fields = [
            'id',
            'room',
            'date',
            'dateend',
            'jalali_date',
            'jalali_dateend',
            'original_price',
            'discounted_price',
            'extra_passenger_price',
            'foreign_passenger_price',
            'discount',
        ]

    def get_jalali_date(self, obj):
        try:
            if isinstance(obj.date, jdatetime.date):
                return obj.date.strftime('%Y/%m/%d')
            return jdatetime.date.fromgregorian(date=obj.date).strftime('%Y/%m/%d')
        except Exception:
            return 'تاریخ نامعتبر'

    def get_jalali_dateend(self, obj):
        try:
            if isinstance(obj.dateend, jdatetime.date):
                return obj.dateend.strftime('%Y/%m/%d')
            return jdatetime.date.fromgregorian(date=obj.dateend).strftime('%Y/%m/%d')
        except Exception:
            return 'تاریخ نامعتبر'
    
    
class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = (
            'first_name',
            'last_name',
            'is_foreign',
            'national_code',
            'passport_code',
            'phone_number',
        )



class BestHotelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BestHotels
        fields = (
            'order',
            'title_logo',
            'image_logo_hotel',
        )
        
        
        
class ClosedDateSerializer(serializers.ModelSerializer):
    hotel_name = serializers.SerializerMethodField()

    class Meta:
        model = ClosedDate
        fields = ['id','reason', 'room_date', 'date', 'hotel_name']

    def get_hotel_name(self, obj):
        try:
            return obj.room_date.room.hotel.name
        except Exception:
            return 'نامشخص'
