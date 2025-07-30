from rest_framework import serializers
import jdatetime
from django.utils import timezone
from django.db import models
from authentication import models
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
    Room,
    RoomDatePrice,
    RoomFacilities,
    RoomService,
    HotelTag,
    HotelFAQ,
    NearbyPlace,
    Passenger,
    SuggestedCommentItem,
    Comment,
    CommentPoint,
    CommentPointItem,
)

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ('name',)

class CitySerializer(serializers.ModelSerializer):
    province = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('name', 'image', 'province', 'slug', 'hotels_number','show_in_homepage')

    def get_province(self, obj):
        return obj.province.name if obj.province else None

class HotelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelType
        fields = ('id', 'title')

class FavoriteHotelSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    type = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    original_total_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    discount_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            'name', 'slug', 'city', 'address', 'main_image', 'stars', 'type',
            'is_special_offer', 'is_flash_sale', 'is_best_seller',
            'original_total_price', 'total_price', 'rating',
            'discount_percentage', 'discount_expiry'
        )

    def get_type(self, obj):
        return obj.type.title if obj.type else None

    def get_main_image(self, obj):
        request = self.context.get('request')
        image_url = obj.main_image.url if obj.main_image else ''
        return request.build_absolute_uri(image_url) if request else f"https://safarnameh24.com{image_url}"

    def get_total_price(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('total_price', None)

    def get_original_total_price(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('original_total_price', None)

    def get_rating(self, obj):
        return getattr(obj, 'rating', None)

    def get_discount_percentage(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_type = price_data.get('discount_type', 'none')
        discount_value = price_data.get('discount_value', 0)
        if discount_type == 'percentage':
            return discount_value
        elif discount_type == 'fixed':
            original_price = price_data.get('original_total_price', 0)
            if original_price > 0:
                return round((discount_value / original_price) * 100, 1)
        return 0

    def get_discount_expiry(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_date = price_data.get('discount_date', None)
        return discount_date.strftime('%Y-%m-%d') if discount_date else None

class HotelListSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    type = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    original_total_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    discount_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            'name', 'slug', 'city', 'address', 'main_image', 'stars', 'type',
            'is_special_offer', 'is_flash_sale', 'is_best_seller',
            'original_total_price', 'total_price', 'rating',
            'discount_percentage', 'discount_expiry'
        )

    def get_type(self, obj):
        return obj.type.title if obj.type else None

    def get_main_image(self, obj):
        request = self.context.get('request')
        image_url = obj.main_image.url if obj.main_image else ''
        return request.build_absolute_uri(image_url) if request else f"https://safarnameh24.com{image_url}"

    def get_total_price(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('total_price', None)

    def get_original_total_price(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('original_total_price', None)

    def get_rating(self, obj):
        return getattr(obj, 'rating', None)

    def get_discount_percentage(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_type = price_data.get('discount_type', 'none')
        discount_value = price_data.get('discount_value', 0)
        if discount_type == 'percentage':
            return discount_value
        elif discount_type == 'fixed':
            original_price = price_data.get('original_total_price', 0)
            if original_price > 0:
                return round((discount_value / original_price) * 100, 1)
        return 0

    def get_discount_expiry(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_date = price_data.get('discount_date', None)
        return discount_date.strftime('%Y-%m-%d') if discount_date else None

class FacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facilities
        fields = ('id', 'title')

class RoomFacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomFacilities
        fields = ['id', 'title']
        ref_name = "RoomFacilitiesSerializerCustom"

class HotelFacilitiesSerializer(serializers.ModelSerializer):
    facilities = FacilitiesSerializer(many=True, read_only=True)
    room_facilities = RoomFacilitiesSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = ('id', 'name', 'slug', 'facilities', 'room_facilities')

class RoomServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomService
        fields = ('title',)

class HotelTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelTag
        fields = ('title',)

class HotelImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ('main_image', 'image1', 'image2', 'image3', 'image4')

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
            'name', 'city_name', 'latitude', 'longitude', 'best_logo', 'logo_preview',
            'stars', 'address', 'floors_count', 'rooms_count',
            'check_in_time', 'check_out_time'
        )

    def get_logo_preview(self, obj):
        request = self.context.get('request')
        if obj.best_logo and getattr(obj.best_logo, 'image_logo_hotel', None):
            url = obj.best_logo.image_logo_hotel.url
            return request.build_absolute_uri(url) if request else url
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
        fields = ('rules', 'important_notes')

class HotelFAQListSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = HotelFAQ
        fields = ('question', 'answer', 'icon')

    def get_icon(self, obj):
        if not obj.icon:
            return None
        request = self.context.get('request')
        url = request.build_absolute_uri(obj.icon.svg_icon.url) if request and getattr(obj.icon, 'svg_icon', None) else None
        return {"title": obj.icon.title_icon or "", "link": url}

class NearbyPlaceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NearbyPlace
        fields = (
            'title', 'distance', 'driving_time', 'walking_time', 'image', 'latitude', 'longitude'
        )

class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = (
            'id',
            'first_name',
            'last_name',
            'identification_code',
            'phone_number',
        )

class BestHotelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BestHotels
        fields = ('order', 'title_logo', 'image_logo_hotel')

class HotelTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelTag
        fields = ('id', 'title')

class HotelGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelGalleryImage
        fields = ('id', 'image', 'order')

class HotelGallerySerializer(serializers.ModelSerializer):
    images = HotelGalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = HotelGallery
        fields = ('id', 'title', 'hotel', 'images')

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

class SuggestedItemWithRatingSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=SuggestedCommentItem.objects.all(),
        source='suggested_item'
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)

class CommentSerializer(serializers.ModelSerializer):
    strengths = CommentPointItemSerializer(many=True, read_only=True)
    weaknesses = CommentPointItemSerializer(many=True, read_only=True)
    points = CommentPointSerializer(many=True, read_only=True)
    suggested_items = SuggestedCommentItemSerializer(many=True, read_only=True)

    strength_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommentPointItem.objects.filter(is_positive=True),
        write_only=True,
        source='strengths',
        required=False,
        allow_empty=True,
    )
    weakness_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CommentPointItem.objects.filter(is_negative=True),
        write_only=True,
        source='weaknesses',
        required=False,
        allow_empty=True,
    )

    suggested_items_with_rating = SuggestedItemWithRatingSerializer(
        many=True,
        write_only=True,
        required=False,
        source='suggested_items_custom'
    )

    user = serializers.StringRelatedField(read_only=True)
    hotel = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id',
            'text',
            'stars',
            'strength_ids',
            'weakness_ids',
            'suggested_items_with_rating',
            'strengths',
            'weaknesses',
            'suggested_items',
            'points',
            'user',
            'hotel',
            'created',
            'created_jalali'
        ]
        read_only_fields = ['user', 'hotel', 'created', 'created_jalali']
        ref_name = 'CustomCommentSerializer'

    def create(self, validated_data):
        suggested_items_data = validated_data.pop('suggested_items_custom', [])
        comment = super().create(validated_data)
        suggested_item_ids = [item['suggested_item'].id for item in suggested_items_data]
        comment.suggested_items.set(suggested_item_ids)
        for item in suggested_items_data:
            CommentPoint.objects.create(
                comment=comment,
                comment_point_item=item['suggested_item'],
                point=item['rating']
            )
        return comment

    def validate(self, data):
        if not data.get('text'):
            raise serializers.ValidationError({'text': 'این فیلد الزامی است.'})
        if not data.get('stars'):
            raise serializers.ValidationError({'stars': 'این فیلد الزامی است.'})
        return data

class HotelCommentListSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    created_time = serializers.SerializerMethodField()
    strengths = CommentPointItemSerializer(many=True, read_only=True)
    weaknesses = CommentPointItemSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'first_name', 'last_name', 'user_image', 'text',
            'strengths', 'weaknesses', 'stars', 'created_date', 'created_time'
        ]

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user else None

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user else None

    def get_user_image(self, obj):
        user = obj.user
        if user:
            natural_profile = getattr(user, 'natural_profile', None)
            if natural_profile and natural_profile.image:
                request = self.context.get('request')
                url = natural_profile.image.url
                if request:
                    return request.build_absolute_uri(url)
                return url
        return None

    def get_created_date(self, obj):
        if obj.created_jalali:
            return obj.created_jalali.split(" ساعت ")[0]
        return None

    def get_created_time(self, obj):
        if obj.created_jalali and " ساعت " in obj.created_jalali:
            return obj.created_jalali.split(" ساعت ")[1]
        return None

class ClosedDateSerializer(serializers.ModelSerializer):
    month = serializers.SerializerMethodField()

    class Meta:
        model = ClosedDate
        fields = ['date', 'reason', 'user_level', 'month']

    def get_month(self, obj):
        return obj.date.strftime('%B')

class RoomDatePriceSerializer(serializers.ModelSerializer):
    closed_dates = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    user_level = serializers.StringRelatedField()

    class Meta:
        model = RoomDatePrice
        fields = [
            'start_date', 'end_date', 'price', 'extra_passenger_price', 'foreign_passenger_price',
            'discount_type', 'discount_value', 'discount_start', 'discount_end',
            'room_capacity', 'extra_capacity', 'closed_dates', 'month', 'user_level'
        ]

    def get_closed_dates(self, obj):
        closed_qs = obj.closed_dates.filter(date__gte=obj.start_date, date__lte=obj.end_date)
        return ClosedDateSerializer(closed_qs, many=True).data

    def get_month(self, obj):
        return obj.start_date.strftime('%B')

class RoomSerializer(serializers.ModelSerializer):
    services = RoomServiceSerializer(many=True, read_only=True)
    date_prices = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'hotel',
            'title',
            'description',
            'inventory',
            'count',
            'auto_approved_count',
            'customer_club_points',
            'services',
            'date_prices',
            'min_price'
        ]

    def get_date_prices(self, obj):
        user_level = self.context.get('user_level')
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        prices = obj.date_prices.all()

        if start_date and end_date:
            prices = prices.filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

        if user_level:
            prices = prices.filter(
                models.Q(user_level=user_level) | models.Q(user_level__isnull=True)
            )

        def final_price(price_obj):
            price = price_obj.price
            if price_obj.discount_type == 'percentage' and price_obj.discount_value:
                price = price * (100 - price_obj.discount_value) / 100
            elif price_obj.discount_type == 'fixed' and price_obj.discount_value:
                price = price - price_obj.discount_value
            return price

        prices = sorted(prices, key=final_price)
        return RoomDatePriceSerializer(prices, many=True).data

    def get_min_price(self, obj):
        user_level = self.context.get('user_level')
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        prices = obj.date_prices.all()

        if start_date and end_date:
            prices = prices.filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

        if user_level:
            prices = prices.filter(
                models.Q(user_level=user_level) | models.Q(user_level__isnull=True)
            )

        if not prices.exists():
            return None

        def final_price(price_obj):
            price = price_obj.price
            if price_obj.discount_type == 'percentage' and price_obj.discount_value:
                price = price * (100 - price_obj.discount_value) / 100
            elif price_obj.discount_type == 'fixed' and price_obj.discount_value:
                price = price - price_obj.discount_value
            return price

        min_p = min(prices, key=final_price)
        return final_price(min_p)

class RoomFacilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomFacilities
        fields = ['id', 'title']

class HotelSearchSerializer(serializers.Serializer):
    hotels = serializers.SerializerMethodField()
    cities = serializers.SerializerMethodField()

    class Meta:
        fields = ('hotels', 'cities')

    def get_hotels(self, obj):
        hotels = obj.get('hotels', [])
        return [
            {
                'id': hotel.id,
                'name': hotel.name,
                'city': {
                    'id': hotel.city.id,
                    'name': hotel.city.name,
                    'province': {'name': hotel.city.province.name},
                    'slug': hotel.city.slug
                },
                'slug': hotel.slug,
                'stars': hotel.stars  # حذف شرط or ''
            }
            for hotel in hotels
        ]

    def get_cities(self, obj):
        cities = obj.get('cities', [])
        return [
            {
                'id': city.id,
                'name': city.name,
                'province': {'name': city.province.name},
                'slug': city.slug,
                'hotels_number': city.hotels.count()
            }
            for city in cities
        ]