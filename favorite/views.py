from rest_framework import generics, permissions
from .models import FavoriteCollection
from .serializers import FavoriteCollectionSerializer, FavoriteCollectionCreateSerializer


# ---- Hotel Collections ----
class HotelFavoriteCollectionListCreateAPI(generics.ListCreateAPIView):
    """
    لیست و ایجاد کالکشن هتل‌ها

    - **GET**: دریافت لیست کالکشن‌های هتل کاربر  
    - **POST**: ایجاد کالکشن جدید برای هتل‌ها
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user, favorites__item_content_type__model="hotel").distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FavoriteCollectionCreateSerializer
        return FavoriteCollectionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HotelFavoriteCollectionDetailAPI(generics.RetrieveDestroyAPIView):
    """
    جزئیات/حذف کالکشن هتل‌ها
    """
    serializer_class = FavoriteCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user, favorites__item_content_type__model="hotel").distinct()


# ---- Article Collections ----
class ArticleFavoriteCollectionListCreateAPI(generics.ListCreateAPIView):
    """
    لیست و ایجاد کالکشن مقالات

    - **GET**: دریافت لیست کالکشن‌های مقاله کاربر  
    - **POST**: ایجاد کالکشن جدید برای مقالات
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user, favorites__item_content_type__model="article").distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FavoriteCollectionCreateSerializer
        return FavoriteCollectionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ArticleFavoriteCollectionDetailAPI(generics.RetrieveDestroyAPIView):
    """
    جزئیات/حذف کالکشن مقالات
    """
    serializer_class = FavoriteCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user, favorites__item_content_type__model="article").distinct()
