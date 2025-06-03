from rest_framework import serializers
from .models import (
    ComingSoon,
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
    StatisticItem,
    UserLevel,
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
        )

class StatisticItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatisticItem
        fields = (
            'title',
            'subtitle',
        )

class StatisticSerializer(serializers.ModelSerializer):
    items = StatisticItemSerializer(many=True, read_only=True)

    class Meta:
        model = Statistic
        fields = (
            'title',
            'description',
            'image',
            'items',
        )

class ChooseReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChooseReason
        exclude = (
            'id',
        )


class FAQSerializer(serializers.ModelSerializer):
    page_title = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        exclude = ('id',)

    def get_page_title(self, obj):
        try:
            return obj.page.title
        except Exception:
            return None

    
    
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
    page_title = serializers.SerializerMethodField()
    class Meta:
        model = Banner
        exclude = ('id', 'page',)
    def get_page_title(self, obj):
        return obj.page.title if obj.page else None

class EnamadLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnamadLicense
        exclude = (
            'id',
        )

class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        exclude = (
            'id',
        )


class AdvantageSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Advantage
        exclude = ('id',)

    def get_icon(self, obj):
        icon = getattr(obj, 'icon', None)
        if not icon:
            return None  # یا می‌تونی return {} بزاری اگه بخوای ساختار خالی بدی

        request = self.context.get('request', None)

        url = None
        if request and hasattr(icon, 'icon_file') and icon.icon_file:
            try:
                url = request.build_absolute_uri(icon.icon_file.url)
            except Exception:
                url = None

        return {
            "title": getattr(icon, 'title', ''),
            "svg_code": getattr(icon, 'svg_code', ''),
            "url": url
        }



    

class FakeCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FakeComment
        exclude = (
            'id',
        )

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        exclude = (
            'id',
        )

class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLevel
        exclude = (
            'id',
        )
        
       
       
       

class ComingSoonSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    background = serializers.SerializerMethodField()

    class Meta:
        model = ComingSoon
        exclude = ('id',)

    def get_logo(self, obj):
        request = self.context.get('request')
        if obj.logo and hasattr(obj.logo, 'url'):
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_background(self, obj):
        request = self.context.get('request')
        if obj.background and hasattr(obj.background, 'url'):
            return request.build_absolute_uri(obj.background.url)
        return None


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        exclude = ('id',)
