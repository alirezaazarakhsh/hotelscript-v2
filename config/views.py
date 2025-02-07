from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from .serializers import (
    PageSerializer,
    SiteConfigSerializer,
)
from .models import (
    Page,
    SiteConfig,
)

# Create your views here.
class PageListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PageSerializer
    pagination_class = None

    def get_queryset(self):
        return Page.objects.all()

class SiteConfigRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SiteConfigSerializer

    def get_object(self):
        return SiteConfig.objects.first()
