from rest_framework import serializers
from .models import IconShortcut

class IconShortcutSerializer(serializers.ModelSerializer):
    svg_icon_url = serializers.SerializerMethodField()

    class Meta:
        model = IconShortcut
        fields = (
            'order',
            'title_icon',
            'svg_icon_url',
        )

    def get_svg_icon_url(self, obj):
        request = self.context.get('request')
        if obj.svg_icon and request:
            return request.build_absolute_uri(obj.svg_icon.url)
        elif obj.svg_icon:
            return obj.svg_icon.url
        return None
