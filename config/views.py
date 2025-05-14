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
    ChooseReasonSerializer,
    FAQSerializer,
    ServiceSerializer,
    ContactInfoSerializer,
    SocialMediaSerializer,
    BannerSerializer,
    EnamadLicenseSerializer,
    LicenseSerializer,
    AdvantageSerializer,
    FakeCommentSerializer,
    RuleSerializer,
    UserLevelSerializer,
)
from .models import (
    Page,
    HeaderMenu,
    QuickAccess,
    Section,
    SiteConfig,
    Slide,
    Statistic,
    ChooseReason,
    FAQ,
    Service,
    ContactInfo,
    SocialMedia,
    Banner,
    EnamadLicense,
    License,
    Advantage,
    FakeComment,
    Rule,
    UserLevel,
)

# Create your views here.
class PageListView(ListAPIView):
    queryset = Page.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = PageSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class HeaderMenuListView(ListAPIView):
    queryset = HeaderMenu.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = HeaderMenuSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class QuickAccessListView(ListAPIView):
    queryset = QuickAccess.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = QuickAccessSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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
        )],
        tags=['static']
    )
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
    
    @swagger_auto_schema(
        tags=['home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class StatisticListView(ListAPIView):
    queryset = Statistic.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = StatisticSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ChooseReasonListView(ListAPIView):
    queryset = ChooseReason.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ChooseReasonSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class FAQListView(ListAPIView):
    queryset = FAQ.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = FAQSerializer
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
        )],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ServiceListView(ListAPIView):
    queryset = Service.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ServiceSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ContactInfoListView(ListAPIView):
    queryset = ContactInfo.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ContactInfoSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['contact']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class SocialMediaListView(ListAPIView):
    queryset = SocialMedia.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SocialMediaSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['contact']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class BannerListView(ListAPIView):
    queryset = Banner.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = BannerSerializer
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

class EnamadLicenseRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = EnamadLicenseSerializer

    def get_object(self):
        return EnamadLicense.objects.first()

class LicenseListView(ListAPIView):
    queryset = License.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = LicenseSerializer
    pagination_class = None

class AdvantageListView(ListAPIView):
    queryset = Advantage.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = AdvantageSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class FakeCommentListView(ListAPIView):
    queryset = FakeComment.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = FakeCommentSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class RuleListView(ListAPIView):
    queryset = Rule.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RuleSerializer
    pagination_class = None
    
    @swagger_auto_schema(
        tags=['rule']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class UserLevelListView(ListAPIView):
    queryset = UserLevel.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserLevelSerializer
    pagination_class = None