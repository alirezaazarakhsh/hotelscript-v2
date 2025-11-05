# chat_api/serializers.py
from rest_framework import serializers
from settingchatbot.models import FAQ, BotSettings


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True)
    audio_data = serializers.CharField(required=False, allow_null=True) # Base64 audio
    mime_type = serializers.CharField(required=False, allow_null=True)
    # history should be a list of {'sender': 'user'|'bot', 'text': 'message content'}
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=[]
    )

class ChatSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = BotSettings
        fields = [
            'system_instruction',
            'default_voice',
            'is_bot_voice_enabled',
            'welcome_title',
            'welcome_message',
            'logo_url'
        ]

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']
        ref_name = 'ChatbotFAQSerializer'