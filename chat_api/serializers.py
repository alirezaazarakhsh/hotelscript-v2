# chat_api/serializers.py
from rest_framework import serializers
from settingchatbot.models import FAQ # این خط را اضافه کنید


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

class ChatSettingsSerializer(serializers.Serializer):
    # این فیلدها از مدل BotSettings خوانده می‌شوند
    google_api_key = serializers.CharField(read_only=True)
    system_instruction = serializers.CharField(read_only=True)
    default_voice = serializers.CharField(read_only=True)
    is_bot_voice_enabled = serializers.BooleanField(read_only=True)
    available_fonts = serializers.JSONField(read_only=True)
    hotel_links = serializers.JSONField(read_only=True)

# سریالایزر جدید برای مدل FAQ
class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ # مطمئن شوید که FAQ را از settingchatbot.models ایمپورت کرده‌اید
        fields = ['id', 'question', 'answer'] # فقط فیلدهای مورد نیاز را نمایش می‌دهیم
        ref_name = 'ChatbotFAQSerializer' # <--- This is the crucial line to add/change