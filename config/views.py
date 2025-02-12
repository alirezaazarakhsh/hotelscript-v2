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
    SlideSerializer,
    StatisticSerializer,
)
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
    SiteConfig,
    Slide,
    Statistic,
)

# Create your views here.
class PageListView(ListAPIView):
    queryset = Page.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = PageSerializer
    pagination_class = None

class HeaderMenuListView(ListAPIView):
    queryset = HeaderMenu.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = HeaderMenuSerializer
    pagination_class = None

class QuickAccessListView(ListAPIView):
    queryset = QuickAccess.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = QuickAccessSerializer
    pagination_class = None

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

class SlideListView(ListAPIView):
    queryset = Slide.actives.all()
    permission_classes = (AllowAny,)
    serializer_class = SlideSerializer
    pagination_class = None

class StatisticListView(ListAPIView):
    queryset = Statistic.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = StatisticSerializer
    pagination_class = None
