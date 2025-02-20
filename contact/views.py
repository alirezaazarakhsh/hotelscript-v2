from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    CreateAPIView,
)
from .serializers import (
    ContactMessageSerializer,
)
from .models import (
    ContactMessage,
)

# Create your views here.
class ContactMessageCreateView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ContactMessageSerializer
