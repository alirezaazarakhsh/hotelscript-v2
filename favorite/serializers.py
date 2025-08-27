from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import FavoriteCollection, Favorite
from blog.models import Article  # مدل مقاله برای ذخیره اطلاعات مقالات
from reservation.models import Hotel  # مدل هتل برای ذخیره اطلاعات هتل‌ها
from datetime import datetime
from jdatetime import datetime as jdatetime  # استفاده از jdatetime برای تبدیل به شمسی

class ArticleSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Article.
    این سریالایزر اطلاعات مقاله شامل تصویر اصلی، خلاصه، محتوا، اسلاگ و تاریخ شمسی را برمی‌گرداند.
    """
    jalali_date = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'main_image', 'summary', 'content', 'slug', 'jalali_date']
        extra_kwargs = {
            'id': {'help_text': 'شناسه یکتای مقاله'},
            'main_image': {'help_text': 'تصویر اصلی مقاله'},
            'summary': {'help_text': 'خلاصه مقاله'},
            'content': {'help_text': 'محتوای کامل مقاله'},
            'slug': {'help_text': 'اسلاگ مقاله برای URL'},
            'jalali_date': {'help_text': 'تاریخ انتشار مقاله به فرمت شمسی'}
        }

    def get_jalali_date(self, obj):
        """
        تبدیل تاریخ میلادی به شمسی برای مقاله.
        """
        if obj.created_at:
            jalali_date = jdatetime.fromgregorian(datetime=obj.created_at)
            return jalali_date.strftime('%Y/%m/%d')
        return None

class HotelSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Hotel.
    این سریالایزر اطلاعات هتل شامل نام، اسلاگ، شهر، آدرس، تصویر اصلی، ستاره‌ها و سایر اطلاعات مرتبط را برمی‌گرداند.
    """
    city = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            'name', 'slug', 'city', 'address', 'main_image', 'stars', 'type',
            'is_special_offer', 'is_flash_sale', 'is_best_seller', 'original_total_price',
            'total_price', 'rating', 'discount_percentage', 'discount_expiry',
            'reservation_count', 'average_score'
        ]
        extra_kwargs = {
            'name': {'help_text': 'نام هتل'},
            'slug': {'help_text': 'اسلاگ هتل برای URL'},
            'city': {'help_text': 'اطلاعات شهر هتل'},
            'address': {'help_text': 'آدرس کامل هتل'},
            'main_image': {'help_text': 'تصویر اصلی هتل'},
            'stars': {'help_text': 'تعداد ستاره‌های هتل'},
            'type': {'help_text': 'نوع اقامتگاه (هتل، اقامتگاه و غیره)'},
            'is_special_offer': {'help_text': 'آیا هتل پیشنهاد ویژه دارد؟'},
            'is_flash_sale': {'help_text': 'آیا هتل در فروش فوری است؟'},
            'is_best_seller': {'help_text': 'آیا هتل پرفروش است؟'},
            'original_total_price': {'help_text': 'قیمت اصلی هتل'},
            'total_price': {'help_text': 'قیمت نهایی هتل'},
            'rating': {'help_text': 'امتیاز هتل'},
            'discount_percentage': {'help_text': 'درصد تخفیف'},
            'discount_expiry': {'help_text': 'تاریخ انقضای تخفیف'},
            'reservation_count': {'help_text': 'تعداد رزروهای هتل'},
            'average_score': {'help_text': 'امتیاز میانگین هتل'}
        }

    def get_city(self, obj):
        """
        دریافت اطلاعات شهر مرتبط با هتل.
        """
        return {
            'id': obj.city.id,
            'image': obj.city.image.url if obj.city.image else None,
            'name': obj.city.name,
            'province': obj.city.province,
            'slug': obj.city.slug,
            'hotels_number': obj.city.hotels_number,
            'show_in_homepage': obj.city.show_in_homepage
        }

class FavoriteCollectionSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل FavoriteCollection.
    این سریالایزر اطلاعات مجموعه علاقمندی شامل شناسه، عنوان و حداکثر سه تصویر از آیتم‌های داخل مجموعه را برمی‌گرداند.
    """
    images = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteCollection
        fields = ['id', 'title', 'images']
        extra_kwargs = {
            'id': {'help_text': 'شناسه یکتای مجموعه علاقمندی'},
            'title': {'help_text': 'عنوان مجموعه علاقمندی'},
            'images': {'help_text': 'لیست حداکثر سه تصویر از آیتم‌های داخل مجموعه'}
        }

    def get_images(self, obj):
        """
        دریافت حداکثر سه تصویر از آیتم‌های مورد علاقه در مجموعه.
        """
        favorites = obj.favorites.all()[:3]
        images = []
        for favorite in favorites:
            if favorite.item_content_type.model == 'article':
                article = favorite.item
                if article.main_image:
                    images.append(article.main_image.url)
            elif favorite.item_content_type.model == 'hotel':
                hotel = favorite.item
                if hotel.main_image:
                    images.append(hotel.main_image.url)
        return images

class FavoriteDetailSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Favorite.
    این سریالایزر اطلاعات آیتم‌های مورد علاقه (مقاله یا هتل) را بر اساس نوع محتوا برمی‌گرداند.
    """
    item = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ['item']
        extra_kwargs = {
            'item': {'help_text': 'جزئیات آیتم مورد علاقه (مقاله یا هتل)'}
        }

    def get_item(self, obj):
        """
        دریافت اطلاعات آیتم بر اساس نوع محتوا (مقاله یا هتل).
        """
        if obj.item_content_type.model == 'article':
            return ArticleSerializer(obj.item).data
        elif obj.item_content_type.model == 'hotel':
            return HotelSerializer(obj.item).data
        return None