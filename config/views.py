from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from .serializers import (
    PageSerializer,
    HeaderMenuSerializer,
    QuickAccessSerializer,
    SiteConfigSerializer,
)
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    SiteConfig,
)

# Create your views here.
class PageListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PageSerializer
    pagination_class = None

    def get_queryset(self):
        return Page.objects.all()

class HeaderMenuListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HeaderMenuSerializer
    pagination_class = None

    def get_queryset(self):
        return HeaderMenu.objects.all()

class QuickAccessListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = QuickAccessSerializer
    pagination_class = None

    def get_queryset(self):
        return QuickAccess.objects.all()

class SiteConfigRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SiteConfigSerializer

    def get_object(self):
        return SiteConfig.objects.first()
