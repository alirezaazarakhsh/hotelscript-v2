from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import FavoriteCollection, Favorite
from .serializers import FavoriteCollectionSerializer, FavoriteCollectionCreateSerializer


# ------------------ هتل ------------------

class HotelFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست و ایجاد کالکشن هتل‌ها",
        operation_description="""
        - **GET**: دریافت تمام لیست‌های علاقمندی هتل متعلق به کاربر وارد شده  
        - **POST**: ایجاد کالکشن جدید برای هتل‌ها (فقط نام لیست لازم است)
        """,
        tags=["favorites-hotels"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={200: FavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="hotel"
        ).distinct()
        serializer = FavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HotelFavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="جزئیات یک کالکشن هتل",
        operation_description="دریافت جزئیات و آیتم‌های داخل یک کالکشن هتل (بر اساس id کالکشن)",
        tags=["favorites-hotels"],
        responses={200: FavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="hotel"
        ).distinct().first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = FavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف کالکشن هتل",
        operation_description="حذف کامل یک کالکشن هتل (تمام آیتم‌های داخل آن نیز حذف می‌شوند)",
        tags=["favorites-hotels"],
    )
    def delete(self, request, pk):
        collection = FavoriteCollection.objects.filter(user=request.user, id=pk).first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------ مقاله ------------------

class ArticleFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست و ایجاد کالکشن مقالات",
        operation_description="""
        - **GET**: دریافت تمام لیست‌های علاقمندی مقاله متعلق به کاربر وارد شده  
        - **POST**: ایجاد کالکشن جدید برای مقالات (فقط نام لیست لازم است)
        """,
        tags=["favorites-articles"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={200: FavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="article"
        ).distinct()
        serializer = FavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArticleFavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="جزئیات یک کالکشن مقاله",
        operation_description="دریافت جزئیات و آیتم‌های داخل یک کالکشن مقاله (بر اساس id کالکشن)",
        tags=["favorites-articles"],
        responses={200: FavoriteCollectionSerializer},
    )
    def get(self, request, pk):
        collection = FavoriteCollection.objects.filter(
            user=request.user, id=pk, favorites__item_content_type__model="article"
        ).distinct().first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = FavoriteCollectionSerializer(collection, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="حذف کالکشن مقاله",
        operation_description="حذف کامل یک کالکشن مقاله (تمام آیتم‌های داخل آن نیز حذف می‌شوند)",
        tags=["favorites-articles"],
    )
    def delete(self, request, pk):
        collection = FavoriteCollection.objects.filter(user=request.user, id=pk).first()
        if not collection:
            return Response({"detail": "کالکشن یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
