from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status


from .filters import PageFilter
from .serializers import (
    ComingSoonSerializer,
    LegalProfileSubmissionRuleSerializer,
    LocationSerializer,
    PageSerializer,
    HeaderMenuSerializer,
    QuickAccessSerializer,
    # SectionSerializer,
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
    ComingSoon,
    LegalProfileSubmissionRule,
    Location,
    Page,
    HeaderMenu,
    QuickAccess,
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


# ای پی ای لیست صفحات 
class PageListView(ListAPIView):
    queryset = Page.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = PageSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست صفحات ایجاد شده ",
        operation_description="این API تمامی صفحات موجود در سایت را بدون صفحه‌بندی بازمی‌گرداند.",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    

# ای پی ای منو های هدر 
class HeaderMenuListView(ListAPIView):
    queryset = HeaderMenu.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = HeaderMenuSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست منوی هدر",
        operation_description="این API لیست آیتم‌های منوی هدر سایت را بدون صفحه‌بندی بازمی‌گرداند.",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




#ای پی ای درسترسی های سریع
class QuickAccessListView(ListAPIView):
    queryset = QuickAccess.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = QuickAccessSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت دسترسی های سریع در فوتر",
        operation_description="این API لیست دسترسی ها را در فوتر باز می گرداند",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




# ای پی ای بخش تنظیمات و کانفیگ وب سایت برای هدر و فوتر
class SiteConfigRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SiteConfigSerializer

    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات بخش کانفیگ وب سایت",
        operation_description="این API تنظیمات کلی سایت را بازمی‌گرداند که شامل تنظیمات هدر و فوتر می باشد ",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_object(self):
        return SiteConfig.objects.first()



#ای پی ای اسلاید ها در صفحه اصلی 
class SlideListView(ListAPIView):
    queryset = Slide.objects.all().order_by('order')
    permission_classes = (AllowAny,)
    serializer_class = SlideSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت اسلایدر های صفحه اصلی",
        operation_description="این API اسلایدهای صفحه اصلی را بر می‌گرداند",
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
        operation_summary="دریافت تنظیمات سکشن اول درباره ما",
        operation_description="این API تنظیمات سکشن اول صفحه درباره ما را باز میگرداند",
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        # به جای برگشت لیست، فقط اولین رکورد رو برگردون
        instance = self.get_queryset().first()
        if not instance:
            return Response({"detail": "تنظیمات پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)





class ChooseReasonListView(ListAPIView):
    queryset = ChooseReason.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ChooseReasonSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت دلایل انتخاب سایت",
        operation_description="این API دلایل انتخاب سایت توسط کاربران را بازمی‌گرداند.",
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
    

# ای پی ای سوالات متداول وب سایت برای صفحات 
class FAQListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FAQSerializer
    pagination_class = None

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'path',
                openapi.IN_QUERY,
                description="مسیر صفحه (مثال: /rules یا /faqs)",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        operation_summary="دریافت لیست سوالات متداول بر اساس مسیر صفحه",
        operation_description="این API لیست سوالات متداول را بر اساس مسیر صفحه (path) بازمی‌گرداند.",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        path = request.query_params.get('path')

        if not path:
            return Response({"detail": "پارامتر path الزامی است."}, status=400)

        try:
            page_obj = Page.objects.get(path=path)  # فرض بر اینکه فیلد path در مدل Page وجود دارد
        except Page.DoesNotExist:
            return Response({"detail": "صفحه با این مسیر یافت نشد."}, status=404)

        queryset = FAQ.objects.filter(page=page_obj)
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'page_title': page_obj.title,
            'faqs': serializer.data,
        })





# ای پی ای خدمات وب سایت در صفحه در باره ما
class ServiceListView(ListAPIView):
    queryset = Service.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ServiceSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست خدمات درباره ما",
        operation_description="این api خدمات مربوط به درباره ما را بر میگرداند",
        tags=['about']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)





#ای پی ای اطلاعات تماس با ما و فوتر 
class ContactInfoListView(ListAPIView):
    queryset = ContactInfo.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ContactInfoSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات تماس برای صفحه تماس با ما و بخشی از فوتر ",
        operation_description="این API اطلاعات مربوط به بخش اول صفحه تماس با ما می باشد و توی فوتر هم اون بخش مربوط به شماره تماس و ایمیل و آدرس را شامل می شود ",
        tags=['contact']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)





#ای پی ای شبکه اجتماعی تماس با ما + فوتر
class SocialMediaListView(ListAPIView):
    queryset = SocialMedia.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SocialMediaSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست شبکه‌های اجتماعی برای تماس با ما و فوتر",
        operation_description="این API لیست شبکه های اجتماعی مربوط به صفحه تماس با ما و بخش مربوط به شبکه احتماعی فوتر را شامل می شود ",
        tags=['contact']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)





# ای پی ای لیست بنر های وب سایت 
class BannerListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = BannerSerializer
    pagination_class = None

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'path',
                openapi.IN_QUERY,
                description="مسیر صفحه (مثلاً: / یا /about)",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        operation_summary="دریافت لیست بنرها",
        operation_description="این API لیست بنرهای صفحه خاص را بر اساس path بازمی‌گرداند.",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        path = request.query_params.get('path')

        if not path:
            return Response({"detail": "پارامتر path الزامی است."}, status=400)

        if not path.startswith('/'):
            path = '/' + path

        try:
            page_obj = Page.objects.get(path=path)
        except Page.DoesNotExist:
            return Response({"detail": "صفحه‌ای با این مسیر یافت نشد."}, status=404)

        queryset = Banner.objects.filter(page=page_obj).order_by('order')
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'page_title': page_obj.title,
            'banners': serializer.data,
        })




#ای پی ای دریافت اینماد درفوتر وب سایت
class EnamadLicenseRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = EnamadLicenseSerializer

    @swagger_auto_schema(
        operation_summary="دریافت نماد اعتماد در فوتر سایت",
        operation_description="این API اطلاعات نماد اعتماد الکترونیکی سایت را بازمی‌گرداند.",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_object(self):
        return EnamadLicense.objects.first()





#ای پی ای لیست مجوز های فوتر 
class LicenseListView(ListAPIView):
    queryset = License.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = LicenseSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست مجوزها در فوتر ",
        operation_description="این API لیست مجوزهای سایت را در فوتر وب سایت باز میگرداند",
        tags=['static']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




class AdvantageListView(ListAPIView):
    queryset = Advantage.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = AdvantageSerializer
    pagination_class = None

    def get_serializer_context(self):
       
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @swagger_auto_schema(
        operation_summary="دریافت آپشن های صفحه اصلی ",
        operation_description="این API برای سکشن آپشن های صفحه اصلی می باشد ",
        tags=['home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    
    
    

# api اضافه کردن کامنت کاربر در صفحه اصلی 
class FakeCommentListView(ListAPIView):
    queryset = FakeComment.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = FakeCommentSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت دیدگاه‌های مشتریان در صفحه اصلی",
        operation_description="این api کامنت هایی که خودمان تنظیم میکنیم را در صفحه اصلی نشان میدهد",
        tags=['home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    

#ای پی ای صفحه قوانین و مقررات 
class RuleListView(ListAPIView):
    queryset = Rule.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RuleSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت قوانین و مقررات وب سایت ",
        operation_description="این API قوانین و مقررات سایت را بازمی‌گرداند.",
        tags=['rule']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    

# ای پی ای مربوط به ساخت دسترسی برای کاربران سایت 
class UserLevelListView(ListAPIView):
    queryset = UserLevel.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserLevelSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت سطح‌های کاربری",
        operation_description="این API سطوح مختلف کاربری را بازمی‌گرداند.",
        tags=['user']
    )
    def list(self, request, *args, **kwargs):
        # متد اصلی list کلاس پایه را صدا بزنید
        return super().list(request, *args, **kwargs)




#ای پی ای کامینگ سون 
class ComingSoonView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات صفحه کامینگ سون",
        operation_description="این API اطلاعات مربوط به صفحه‌ی کامینگ سون شامل لوگو، پس‌زمینه، عنوان و... را برای نمایش در صفحه‌ی اصلی باز می‌گرداند.",
        tags=['commingsoon']
    )
    def get(self, request, *args, **kwargs):
        instance = ComingSoon.objects.first()
        if not instance:
            return Response({"detail": "موردی یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ComingSoonSerializer(instance, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    
    
    

# ای پی ای کانفیگ تماس با ما
class LocationView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="دریافت کانفیگ تماس با ما",
        operation_description="این API موقعیت جغرافیایی (عرض و طول) مربوط به تماس با ما را برمی‌گرداند.",
        tags=['contact']
    )
    def get(self, request, *args, **kwargs):
        location = Location.objects.first()
        if not location:
            return Response({"detail": "موقعیت تعریف نشده است."}, status=404)
        
        serializer = LocationSerializer(location)
        return Response(serializer.data)




# ای پی ای قوانین ارسال مدارک حقوقی 
class LegalProfileSubmissionRuleView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="دریافت قوانین ارسال مدارک پروفایل حقوقی",
        operation_description="این API اطلاعات مربوط به قوانین ارسال مدارک پروفایل حقوقی شامل توضیحات را برای نمایش در صفحه مربوطه باز می‌گرداند.",
        tags=['juridical-profiles']
    )
    def get(self, request, *args, **kwargs):
        instance = LegalProfileSubmissionRule.objects.first()
        if not instance:
            return Response({"detail": "قوانین یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LegalProfileSubmissionRuleSerializer(instance, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)  # تغییر در این خط
    
    