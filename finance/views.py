from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.generics import (
    ListCreateAPIView,
)
from .models import (
    BankCard,
)
from .serializers import (
    BankCardSerializer,
)

# Create your views here.
class BankCardListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BankCardSerializer

    def get_queryset(self):
        user = self.request.user
        profile_type = self.request.query_params.get('profile_type')

        if profile_type == 'natural':
            profile = user.natural_profile
        elif profile_type == 'juridical':
            profile = user.natural_profile.juridical_profile
        else:
            raise ValidationError({
                'profile_type': 'مقدار نوع پروفایل صحیح نیست!',
            })

        return BankCard.objects.filter(
            profile_object_id=profile.pk,
            profile_content_type=ContentType.objects.get_for_model(profile.__class__)
        )
    
    def perform_create(self, serializer):
        profile_type = self.request.data.get('profile_type')
        if profile_type == 'natural':
            profile = self.request.user.natural_profile
        elif profile_type == 'juridical':
            profile = self.request.user.natural_profile.juridical_profile
        else:
            raise ValidationError({
                'profile_type': 'مقدار نوع پروفایل صحیح نیست!',
            })

        BankCard.objects.create(
            card_number=self.request.data.get('card_number'),
            sheba_number=self.request.data.get('sheba_number'),
            profile_object_id=profile.pk,
            profile_content_type=ContentType.objects.get_for_model(profile.__class__),
        )

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'profile_type',
            openapi.IN_QUERY,
            description="Profile type (options: [natural, juridical])",
            type=openapi.TYPE_STRING,
            required=True,
        ),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)