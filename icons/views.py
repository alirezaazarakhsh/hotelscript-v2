from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from .models import IconShortcut
from .serializers import IconShortcutSerializer

class IconShortcutListCreateView(ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = IconShortcutSerializer

    def get_queryset(self):
        """
        بازگرداندن لیست آیکون‌های شورتکات به ترتیب.
        """
        return IconShortcut.objects.all().order_by('order')

    @swagger_auto_schema(
        operation_summary="لیست آیکون‌های سایت ",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - لیست آیکون‌ها را مشاهده کند
        - اطلاعات آیکون‌ها را دریافت کند
        """,
        responses={
            200: IconShortcutSerializer(many=True),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="افزودن آیکون جدید ",
        operation_description="""
        با استفاده از این API می‌توانید یک آیکون جدید (فایل SVG به همراه عنوان و ترتیب) اضافه کنید.
        """,
        request_body=IconShortcutSerializer,
        responses={201: IconShortcutSerializer()}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
