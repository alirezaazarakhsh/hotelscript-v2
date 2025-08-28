from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from django.contrib.contenttypes.models import ContentType

from .models import FavoriteCollection
from .serializers import (
    FavoriteCollectionCreateSerializer,
    HotelFavoriteCollectionSerializer,
    ArticleFavoriteCollectionSerializer,
)


# ------------------ هتل ------------------
class HotelFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست کالکشن‌های هتل",
        tags=["favorites-panel"],
        responses={200: HotelFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="hotel"
        ).distinct()
        serializer = HotelFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد کالکشن هتل",
        tags=["favorites-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: HotelFavoriteCollectionSerializer},
    )
    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            collection = serializer.save(user=request.user)
            response_serializer = HotelFavoriteCollectionSerializer(collection, context={"request": request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HotelFavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="جزئیات یک کالکشن هتل",
        tags=["favorites-panel"],
        responses={200: HotelFavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="hotel"
        ).distinct().first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = HotelFavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف کالکشن هتل",
        tags=["favorites-panel"],
    )
    def delete(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="hotel"
        ).first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------ مقاله ------------------
class ArticleFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست کالکشن‌های مقاله",
        tags=["favorites-panel"],
        responses={200: ArticleFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="article"
        ).distinct()
        serializer = ArticleFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد کالکشن مقاله",
        tags=["favorites-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: ArticleFavoriteCollectionSerializer},
    )
    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            collection = serializer.save(user=request.user)
            response_serializer = ArticleFavoriteCollectionSerializer(collection, context={"request": request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArticleFavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="جزئیات یک کالکشن مقاله",
        tags=["favorites-panel"],
        responses={200: ArticleFavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="article"
        ).distinct().first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ArticleFavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف کالکشن مقاله",
        tags=["favorites-panel"],
    )
    def delete(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="article"
        ).first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
