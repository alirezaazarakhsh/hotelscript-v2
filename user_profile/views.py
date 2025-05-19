from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import (
    ValidationError,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.generics import (
    ListCreateAPIView,
    DestroyAPIView,
    CreateAPIView,
)
from .models import (
    FavoriteCollection,
    Favorite,
)
from .serializers import (
    FavoriteCollectionSerializer,
    FavoriteCreateSerializer,
)

# Create your views here.
class FavoriteCollectionListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionSerializer

    def get_queryset(self):
        queryset = FavoriteCollection.objects.filter(
            user=self.request.user,
        )

        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class FavoriteCollectionDestroyView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionSerializer

    def get_queryset(self):
        queryset = FavoriteCollection.objects.filter(
            user=self.request.user,
        )

        return queryset

class FavoriteCreateView(CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCreateSerializer

    def get_queryset(self):
        queryset = Favorite.objects.select_related('list')\
            .filter(list__user__id=self.request.user.pk)

        return queryset
    
    def perform_create(self, serializer):
        item_type = serializer.validated_data.pop('item_type')
        item_object_id = serializer.validated_data.get('item_object_id')

        content_type = ContentType.objects.get(model=item_type)

        existing = Favorite.objects.filter(
            list__user=self.request.user,
            item_content_type=content_type,
            item_object_id=item_object_id,
        ).exists()

        if existing:
            raise ValidationError('این آیتم قبلاً در یکی از لیست‌های علاقه‌مندی شما ثبت شده است.')
        
        try:
            model_class = content_type.model_class()
            model_class.objects.get(pk=item_object_id)
        except ObjectDoesNotExist:
            raise ValidationError("آیتم مورد نظر وجود ندارد.")
        
        serializer.validated_data['item_content_type'] = content_type

        return super().perform_create(serializer)

class FavoriteDestroyView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Favorite.objects.select_related('list')\
            .filter(list__user__id=self.request.user.pk)

        return queryset
