from rest_framework import serializers
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

class QuickAccessSerializer(serializers.ModelSerializer):
    page = PageSerializer()
    class Meta:
        model = QuickAccess
        exclude = (
            'id',
        )

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        exclude = (
            'id',
            'page',
        )

class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        exclude = (
            'id',
        )

class SlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slide
        exclude = (
            'id',
            'is_active',
        )

class StatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistic
        exclude = (
            'id',
        )

class ChooseReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChooseReason
        exclude = (
            'id',
        )

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        exclude = (
            'id',
        )

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        exclude = (
            'id',
        )

class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        exclude = (
            'id',
        )

class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMedia
        exclude = (
            'id',
        )

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        exclude = (
            'id',
            'page',
        )

class EnamadLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnamadLicense
        exclude = (
            'id',
        )
