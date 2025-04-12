from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import AllowAny
from .models import (
    StoryCategory,
)
from .serializers import (
    StoryCategorySerializer,
)

# Create your views here.
class StoryCategoryListView(ListAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class StoryCategoryRetrieveView(RetrieveAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer
    lookup_field = 'pk'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
