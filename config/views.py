from rest_framework.permissions import AllowAny
from rest_framework.generics import RetrieveAPIView
from .serializers import (
    SiteConfigSerializer,
)
from .models import (
    SiteConfig,
)

# Create your views here.
class SiteConfigRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SiteConfigSerializer

    def get_object(self):
        return SiteConfig.objects.first()
