from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .filters import (
    PageFilter,
)
from .serializers import (
    PageSerializer,
    HeaderMenuSerializer,
    QuickAccessSerializer,
    SectionSerializer,
    SiteConfigSerializer,
)
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
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

class SectionListView(ListAPIView):
    queryset = Section.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SectionSerializer
    pagination_class = None
    filter_backends = (
        PageFilter,
    )

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'page',
            openapi.IN_QUERY,
            description="Filter by page",
            type=openapi.TYPE_STRING,
            required=True,
        )
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class SiteConfigRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SiteConfigSerializer

    def get_object(self):
        return SiteConfig.objects.first()
