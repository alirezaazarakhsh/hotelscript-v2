from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from django.contrib.contenttypes.models import ContentType

from .models import FavoriteCollection, Favorite
from .serializers import (
    FavoriteCollectionCreateSerializer,
    FavoriteCollectionDetailSerializer,
    BaseFavoriteCollectionSerializer,
    FavoriteItemSerializer,
)


# ------------------ لیست کالکشن‌ها ------------------
class FavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="📌 دریافت لیست کالکشن‌های علاقه‌مندی",
        operation_description="""
        این API تمامی کالکشن‌های علاقه‌مندی (چه هتل و چه مقاله) را نمایش می‌دهد.
        هر کالکشن شامل شناسه، عنوان و تعدادی تصویر thumbnail از آیتم‌های داخل لیست است.
        """,
        tags=["favorite-panel"],
        responses={200: BaseFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(user=request.user)
        serializer = BaseFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="➕ ایجاد کالکشن علاقه‌مندی جدید",
        operation_description="""
        با این API می‌توانید یک لیست علاقه‌مندی جدید ایجاد کنید.
        فقط کافی است عنوان (title) لیست را ارسال نمایید.
        """,
        tags=["favorite-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: BaseFavoriteCollectionSerializer},
    )
    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            collection = serializer.save(user=request.user)
            return Response(BaseFavoriteCollectionSerializer(collection, context={"request": request}).data, status=201)
        return Response(serializer.errors, status=400)


# ------------------ جزئیات کالکشن ------------------
class FavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="📖 جزئیات یک کالکشن",
        operation_description="""
        این API جزئیات کامل یک کالکشن خاص را برمی‌گرداند.
        شامل لیست کامل آیتم‌ها (مقالات یا هتل‌ها) به همراه اطلاعات خلاصه هر آیتم.
        """,
        tags=["favorite-panel"],
        responses={200: FavoriteCollectionDetailSerializer},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        return Response(FavoriteCollectionDetailSerializer(collection, context={"request": request}).data)

    @swagger_auto_schema(
        operation_summary="🗑️ حذف یک کالکشن",
        operation_description="با این API می‌توانید یک کالکشن کامل را حذف کنید.",
        tags=["favorite-panel"],
    )
    def delete(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        collection.delete()
        return Response(status=204)


# ------------------ مدیریت آیتم‌های داخل کالکشن ------------------
class FavoriteItemListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="📌 دریافت آیتم‌های داخل یک کالکشن",
        operation_description="این API تمامی آیتم‌های (هتل یا مقاله) داخل یک کالکشن خاص را نمایش می‌دهد.",
        tags=["favorite-panel"],
        responses={200: FavoriteItemSerializer(many=True)},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        return Response(FavoriteItemSerializer(collection.favorites.all(), many=True, context={"request": request}).data)

    @swagger_auto_schema(
        operation_summary="➕ افزودن آیتم به یک کالکشن",
        operation_description="""
        برای افزودن آیتم جدید به یک کالکشن باید نوع (type) و شناسه (id) آیتم را ارسال کنید.
        - type: hotel یا article
        - id: شناسه آیتم
        """,
        tags=["favorite-panel"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "type": openapi.Schema(type=openapi.TYPE_STRING, description="نوع آیتم: hotel یا article"),
                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="شناسه آیتم"),
            },
            required=["type", "id"]
        ),
        responses={201: FavoriteItemSerializer},
    )
    def post(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        item_type = request.data.get("type")
        item_id = request.data.get("id")

        content_type = get_object_or_404(ContentType, model=item_type)
        favorite = Favorite.objects.create(list=collection, item_content_type=content_type, item_object_id=item_id)
        return Response(FavoriteItemSerializer(favorite, context={"request": request}).data, status=201)


class FavoriteItemDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="🗑️ حذف آیتم از کالکشن",
        operation_description="این API یک آیتم خاص (هتل یا مقاله) را از داخل کالکشن حذف می‌کند.",
        tags=["favorite-panel"],
    )
    def delete(self, request, pk, item_id):
        favorite = get_object_or_404(Favorite, id=item_id, list__id=pk, list__user=request.user)
        favorite.delete()
        return Response(status=204)
