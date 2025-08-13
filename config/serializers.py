from rest_framework import serializers
from html.parser import HTMLParser

from .models import (
    ComingSoon,
    LegalProfileSubmissionRule,
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
    icon = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        exclude = ('id',)

    def get_page_title(self, obj):
        try:
            return obj.page.title
        except Exception:
            return None

    def get_icon(self, obj):
        icon = getattr(obj, 'icon', None)
        if not icon:
            return None

        request = self.context.get('request', None)
        url = request.build_absolute_uri(icon.svg_icon.url) if request and icon.svg_icon else None

        return {
            "title": icon.title_icon or "",
            "link": url,
        }


    
    
class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        exclude = (
            'id',
        )


class ContactInfoSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = ContactInfo
        exclude = ('id',)

    def get_icon(self, obj):
        icon = obj.icon
        if not icon:
            return None

        request = self.context.get('request', None)
        url = request.build_absolute_uri(icon.svg_icon.url) if request and icon.svg_icon else None

        return {
            "title": icon.title_icon or "",
            "link": url,
        }




class SocialMediaSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()

    class Meta:
        model = SocialMedia
        exclude = ('id',)

    def get_icon(self, obj):
        icon = getattr(obj, 'icon', None)
        if not icon:
            return None

        request = self.context.get('request', None)
        url = request.build_absolute_uri(icon.svg_icon.url) if request and icon.svg_icon else None

        return {
            "title": icon.title_icon or "",
            "url": url,
        }



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
        icon = obj.icon
        if not icon:
            return None

        request = self.context.get('request', None)
        url = request.build_absolute_uri(icon.svg_icon.url) if request and icon.svg_icon else None

        return {
            "title": icon.title_icon or "",
            "url": url,
        }






class FakeCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FakeComment
        exclude = (
            'id',
        )


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class RuleSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()

    class Meta:
        model = Rule
        fields = ('tab_title', 'text', 'order')

    def get_text(self, obj):
        return strip_tags(obj.text)




class UserLevelSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserLevel
        fields = ['title', 'color', 'icon']  # فقط فیلدهای مورد نیاز را سریالایز می‌کنیم

    def get_icon(self, obj):
        if not hasattr(obj, 'icon') or not obj.icon:
            return None

        icon = obj.icon
        request = self.context.get('request')
        url = None
        if request and getattr(icon, 'svg_icon', None):
            try:
                url = request.build_absolute_uri(icon.svg_icon.url)
            except AttributeError:
                url = None

        return {
            'title': getattr(icon, 'title_icon', '') or '',
            'url': url
        }

        
       
       
       

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



class LegalProfileSubmissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalProfileSubmissionRule
        fields = (
            'description',
        )