from tokenize import Comment
from rest_framework import serializers
from .models import (
    BestHotels,
    ClosedDate,
    HotelGallery,
    HotelGalleryImage,
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
    Room,
    RoomDate,
    Passenger,
    SuggestedCommentItem,
    Comment,
    CommentPoint,
    CommentPointItem,
    SuggestedCommentItem
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
        return obj.type.title if obj.type else None

    def get_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('total_price', None)

    def get_original_total_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('original_total_price', None)

    def get_rating(self, obj):
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
        fields = ('id', 'title')

class RoomFacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomFacilities
        fields = ('id', 'title')

class HotelFacilitiesSerializer(serializers.ModelSerializer):
    facilities = FacilitiesSerializer(many=True, read_only=True)
    room_facilities = RoomFacilitiesSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = (
            'id',
            'name',
            'slug',
            'facilities',
            'room_facilities',
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
    city_name = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            'name',
            'city_name',
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
        request = self.context.get('request')
        if obj.best_logo and obj.best_logo.image_logo_hotel:
            url = obj.best_logo.image_logo_hotel.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_city_name(self, obj):
        return obj.city.name if obj.city else None

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
    icon = serializers.SerializerMethodField()

    class Meta:
        model = HotelFAQ
        fields = (
            'question',
            'answer',
            'icon',
        )

    def get_icon(self, obj):
        icon = getattr(obj, 'icon', None)
        if not icon:
            return None

        request = self.context.get('request', None)
        url = request.build_absolute_uri(icon.svg_icon.url) if request and icon.svg_icon else None

        return {
            "title": icon.title_icon or "",
            "link": url,
        }

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

class HotelTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelTag
        fields = (
            'id',
            'title',
        )
        
class HotelGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelGalleryImage
        fields = (
            'id',
            'image',
            'order',
        )

class HotelGallerySerializer(serializers.ModelSerializer):
    images = HotelGalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = HotelGallery
        fields = (
            'id',
            'title',
            'hotel',
            'images',
        )






class SuggestedCommentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedCommentItem
        fields = ['id', 'title']
        ref_name = "SuggestedCommentItemSerializer"

class CommentPointSerializer(serializers.ModelSerializer):
    comment_point_item = SuggestedCommentItemSerializer(read_only=True)
    comment_point_item_id = serializers.PrimaryKeyRelatedField(
        queryset=SuggestedCommentItem.objects.all(),
        source='comment_point_item',
        write_only=True
    )

    class Meta:
        model = CommentPoint
        fields = ['id', 'comment_point_item', 'comment_point_item_id', 'point']
        ref_name = "CommentPointSerializer"

class CommentPointItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentPointItem
        fields = ['id', 'title', 'is_positive', 'is_negative']
        ref_name = "CommentPointItemSerializer"

class CommentSerializer(serializers.ModelSerializer):
    # نمایش strengths و weaknesses به صورت nested خواندنی
    strengths = CommentPointItemSerializer(many=True, read_only=True)
    weaknesses = CommentPointItemSerializer(many=True, read_only=True)
    points = CommentPointSerializer(many=True, read_only=True)

    # دریافت strengths و weaknesses به صورت لیست شناسه‌ها برای نوشتن
    strength_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommentPointItem.objects.filter(is_positive=True),
        write_only=True,
        source='strengths'
    )
    weakness_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommentPointItem.objects.filter(is_negative=True),
        write_only=True,
        source='weaknesses'
    )

    # دریافت points به صورت قابل نوشتن
    points = CommentPointSerializer(many=True)

    class Meta:
        model = Comment
        fields = [
            'id',
            'user',
            'hotel',
            'text',
            'strengths',
            'strength_ids',
            'weaknesses',
            'weakness_ids',
            'stars',
            'is_approved',
            'created',
            'created_jalali',
            'points',
        ]
        read_only_fields = ['created', 'created_jalali', 'is_approved']
        ref_name = "CommentSerializerHotel"

    def create(self, validated_data):
        strengths = validated_data.pop('strengths', [])
        weaknesses = validated_data.pop('weaknesses', [])
        points_data = validated_data.pop('points', [])

        comment = Comment.objects.create(**validated_data)
        comment.strengths.set(strengths)
        comment.weaknesses.set(weaknesses)

        for point_data in points_data:
            CommentPoint.objects.create(comment=comment, **point_data)

        return comment

    def update(self, instance, validated_data):
        strengths = validated_data.pop('strengths', None)
        weaknesses = validated_data.pop('weaknesses', None)
        points_data = validated_data.pop('points', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if strengths is not None:
            instance.strengths.set(strengths)
        if weaknesses is not None:
            instance.weaknesses.set(weaknesses)

        if points_data is not None:
            instance.points.all().delete()
            for point_data in points_data:
                CommentPoint.objects.create(comment=instance, **point_data)

        return instance
