from rest_framework import serializers
from .models import (
    Page,
    SiteConfig,
)

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        exclude = (
            'id',
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
    