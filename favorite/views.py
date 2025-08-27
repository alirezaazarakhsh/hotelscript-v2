from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import FavoriteCollection, Favorite
from .serializers import FavoriteCollectionSerializer, FavoriteDetailSerializer
from django.contrib.contenttypes.models import ContentType
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from blog.models import Article
from reservation.models import Hotel

class FavoriteCollectionListView(APIView):
    """
    دریافت لیست تمام مجموعه‌های علاقمندی کاربر جاری.
    این API تمام مجموعه‌های کاربر را با حداکثر سه تصویر از آیتم‌های هر مجموعه برمی‌گرداند.
    """
    @swagger_auto_schema(
        operation_summary="لیست مجموعه‌های علاقمندی",
        operation_description="دریافت لیست تمام مجموعه‌های علاقمندی کاربر جاری با حداکثر سه تصویر از آیتم‌های هر مجموعه",
        responses={200: FavoriteCollectionSerializer(many=True)},
        tags=['Favorite-panel']
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(user=request.user)
        serializer = FavoriteCollectionSerializer(collections, many=True)
        response_data = {
            'count': collections.count(),
            'total_pages': 1,  # برای سادگی، فرض می‌کنیم صفحه‌بندی نداریم
            'current_page': 1,
            'results': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

class FavoriteCollectionDetailView(APIView):
    """
    دریافت جزئیات آیتم‌های یک مجموعه علاقمندی بر اساس نوع محتوا (blog یا hotel).
    این API آیتم‌های مورد علاقه (مقاله یا هتل) را برای یک مجموعه خاص فیلتر می‌کند.
    """
    @swagger_auto_schema(
        operation_summary="جزئیات مجموعه علاقمندی",
        operation_description="دریافت جزئیات آیتم‌های یک مجموعه علاقمندی بر اساس نوع محتوا (blog یا hotel)",
        responses={200: FavoriteDetailSerializer(many=True)},
        tags=['Favorite-panel']
    )
    def get(self, request, collection_id, content_type):
        collection = get_object_or_404(FavoriteCollection, id=collection_id, user=request.user)
        
        # فیلتر کردن بر اساس نوع محتوا
        content_type_map = {
            'blog': 'article',
            'hotel': 'hotel'
        }
        
        if content_type not in content_type_map:
            return Response({'error': 'نوع محتوا نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        model = content_type_map[content_type]
        try:
            content_type_obj = ContentType.objects.get_for_model(Hotel if model == 'hotel' else Article)
        except ContentType.DoesNotExist:
            return Response({'error': f'نوع محتوا {model} یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        favorites = Favorite.objects.filter(
            list=collection,
            item_content_type=content_type_obj
        )
        
        serializer = FavoriteDetailSerializer(favorites, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FavoriteCollectionDeleteView(APIView):
    """
    حذف یک مجموعه علاقمندی توسط کاربر مالک آن.
    این API مجموعه مورد نظر را حذف می‌کند، مشروط بر اینکه کاربر درخواست‌دهنده مالک آن باشد.
    """
    @swagger_auto_schema(
        operation_summary="حذف مجموعه علاقمندی",
        operation_description="حذف یک مجموعه علاقمندی توسط کاربر مالک آن",
        responses={
            204: 'مجموعه با موفقیت حذف شد',
            403: 'کاربر مجاز به حذف این مجموعه نیست',
            404: 'مجموعه یافت نشد'
        },
        tags=['Favorite-panel']
    )
    def delete(self, request, collection_id):
        collection = get_object_or_404(FavoriteCollection, id=collection_id)
        if collection.user != request.user:
            return Response({'error': 'شما مجاز به حذف این مجموعه نیستید'}, status=status.HTTP_403_FORBIDDEN)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)