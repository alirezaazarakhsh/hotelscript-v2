from rest_framework import serializers
from .models import (
    SiteConfig,
)

class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = (
            'header_logo',
            'header_title',
            'header_sub_title',
            'footer_logo',
            'footer_title',
            'footer_description',
        )
    