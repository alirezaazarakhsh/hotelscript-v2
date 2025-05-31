from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from drf_yasg.utils import swagger_auto_schema
from .serializers import ContactMessageSerializer
from .models import ContactMessage

class ContactMessageCreateView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ContactMessageSerializer

    @swagger_auto_schema(
        operation_summary="رسال پیام در تماس با ما",
        operation_description="این API برای ارسال پیام در صفحه تماس با ما می باشد ",
        tags=['contact']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
