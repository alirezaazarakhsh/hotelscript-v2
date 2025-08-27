from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import FavoriteCollection, Favorite


class FavoriteCollectionSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل FavoriteCollection (لیست‌های علاقمندی).
    این سریالایزر اطلاعات لیست علاقمندی شامل:
      - شناسه
      - نام لیست
      - شناسه کاربر
    را برمی‌گرداند.
    """
    class Meta:
        model = FavoriteCollection
        fields = ['id', 'title', 'user']


class FavoriteSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل Favorite (آیتم‌های داخل لیست علاقمندی).
    این سریالایزر اطلاعات زیر را برمی‌گرداند:
      - شناسه
      - لیست علاقمندی
      - نوع آیتم (ContentType)
      - شناسه آیتم
      - رشته نمایش آیتم
    """
    item_content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field="model"
    )
    item_str = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ['id', 'list', 'item_content_type', 'item_object_id', 'item_str']

    def get_item_str(self, obj):
        """
        گرفتن متن نمایشی آیتم (مثلاً عنوان مقاله یا نام هتل)
        """
        return str(obj.item)
