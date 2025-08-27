from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import FavoriteCollection
from .serializers import FavoriteCollectionSerializer, FavoriteCollectionCreateSerializer


# ------------------ هتل ------------------

class HotelFavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="لیست کالکشن‌های هتل",
        operation_description="""
        دریافت تمام کالکشن‌های هتل متعلق به کاربر وارد شده.  
        - هر کالکشن شامل آیتم‌های مرتبط با هتل می‌باشد.
        """,
        tags=["favorites-panel"],
        responses={200: FavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="hotel"
        ).distinct()
        serializer = FavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد کالکشن هتل",
        operation_description="ایجاد یک کالکشن جدید برای هتل‌ها. تنها نام کالکشن مورد نیاز است.",
        tags=["favorites-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: FavoriteCollectionSerializer},
    )
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
        operation_description="دریافت جزئیات و آیتم‌های داخل یک کالکشن هتل بر اساس شناسه کالکشن",
        tags=["favorites-panel"],
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
        operation_description="حذف کامل یک کالکشن هتل و تمام آیتم‌های داخل آن",
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
        operation_description="""
        دریافت تمام کالکشن‌های مقاله متعلق به کاربر وارد شده.  
        - هر کالکشن شامل آیتم‌های مرتبط با مقاله می‌باشد.
        """,
        tags=["favorites-panel"],
        responses={200: FavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(
            user=request.user, favorites__item_content_type__model="article"
        ).distinct()
        serializer = FavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد کالکشن مقاله",
        operation_description="ایجاد یک کالکشن جدید برای مقالات. تنها نام کالکشن مورد نیاز است.",
        tags=["favorites-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: FavoriteCollectionSerializer},
    )
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
        operation_description="دریافت جزئیات و آیتم‌های داخل یک کالکشن مقاله بر اساس شناسه کالکشن",
        tags=["favorites-panel"],
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
        operation_description="حذف کامل یک کالکشن مقاله و تمام آیتم‌های داخل آن",
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
