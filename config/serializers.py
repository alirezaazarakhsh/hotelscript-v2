from rest_framework import serializers
from .models import (
    Page,
    HeaderMenu,
    SiteConfig,
)

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        exclude = (
            'id',
        )
    
class HeaderMenuSerializer(serializers.ModelSerializer):
    page = PageSerializer()
    class Meta:
        model = HeaderMenu
        exclude = (
            'id',
        )

class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        exclude = (
            'id',
        )
    