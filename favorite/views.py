from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from .models import FavoriteCollection, Favorite
from .serializers import (
    FavoriteCollectionCreateSerializer,
    HotelFavoriteCollectionSerializer,
    ArticleFavoriteCollectionSerializer,
    FavoriteItemSerializer,
)


# ------------------ هتل ------------------
class HotelFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست علاقه‌مندی‌های هتل",
        tags=["favorites"],
        responses={200: HotelFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="hotel"
        ).distinct()
        serializer = HotelFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد لیست علاقه‌مندی هتل",
        tags=["favorites"],
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
        operation_summary="جزئیات لیست علاقه‌مندی هتل",
        tags=["favorites"],
        responses={200: HotelFavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = get_object_or_404(
            FavoriteCollection.objects.filter(user=request.user, favorites__item_content_type__model="hotel").distinct(),
            id=pk,
        )
        serializer = HotelFavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف یک لیست علاقه‌مندی هتل",
        tags=["favorites"],
    )
    def delete(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HotelFavoriteItemRemoveAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="حذف آیتم هتل از یک لیست",
        tags=["favorites"],
    )
    def delete(self, request, collection_id, item_id):
        favorite = get_object_or_404(
            Favorite, id=item_id, list__id=collection_id, list__user=request.user
        )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------ مقاله ------------------
class ArticleFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست علاقه‌مندی‌های مقاله",
        tags=["favorites"],
        responses={200: ArticleFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="article"
        ).distinct()
        serializer = ArticleFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد لیست علاقه‌مندی مقاله",
        tags=["favorites"],
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
        operation_summary="جزئیات لیست علاقه‌مندی مقاله",
        tags=["favorites"],
        responses={200: ArticleFavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = get_object_or_404(
            FavoriteCollection.objects.filter(user=request.user, favorites__item_content_type__model="article").distinct(),
            id=pk,
        )
        serializer = ArticleFavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف یک لیست علاقه‌مندی مقاله",
        tags=["favorites"],
    )
    def delete(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArticleFavoriteItemRemoveAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="حذف آیتم مقاله از یک لیست",
        tags=["favorites"],
    )
    def delete(self, request, collection_id, item_id):
        favorite = get_object_or_404(
            Favorite, id=item_id, list__id=collection_id, list__user=request.user
        )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
