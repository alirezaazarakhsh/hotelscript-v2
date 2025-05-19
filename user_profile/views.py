from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.generics import (
    ListCreateAPIView,
    DestroyAPIView,
)
from .models import (
    FavoriteCollection,
)
from .serializers import (
    FavoriteCollectionSerializer,
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
