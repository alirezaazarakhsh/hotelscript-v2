# chat_api/views.py
import json
import base64
import logging
import os
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from google.generativeai import GenerativeModel, configure
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from google.generativeai.protos import GenerationConfig
from google.generativeai.client import get_default_retriever_async_client
from google.generativeai.types import Tool
from google.generativeai.operations import WaitIterator
from google.generativeai.protos import (
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
)
from google.generativeai.types.generation_types import (
    Candidate,
    GenerateContentResponse,
    Part,
    RetrieveContentResponse,
    SpeechConfig,
    TextPart,
    ToolConfig,
    ToolFunction,
    ToolUse,
    ToolUseResponse,
    Modality
)

from settingchatbot.models import BotSettings, FAQ
from .serializers import ChatMessageSerializer, ChatSettingsSerializer, FAQSerializer

# For Swagger documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny # Assuming you might use this for some public endpoints

logger = logging.getLogger(__name__)

# Safety settings (optional, you can customize)
safety_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
]

class ChatbotMessageView(APIView):
    @swagger_auto_schema(
        operation_summary="ارسال پیام به چت‌بات و دریافت پاسخ",
        operation_description="""
        این API برای ارسال پیام متنی یا صوتی به مدل Gemini استفاده می‌شود و پاسخ چت‌بات را برمی‌گرداند.
        همچنین می‌تواند تاریخچه گفتگو را برای حفظ زمینه (context) دریافت کند.

        **ورودی‌ها**:
        - `message` (اختیاری): متن پیام کاربر.
        - `audio_data` (اختیاری): داده صوتی پیام کاربر به صورت Base64.
        - `mime_type` (اختیاری): نوع MIME داده صوتی (مثال: `audio/webm`).
        - `conversation_history` (اختیاری): لیستی از پیام‌های قبلی گفتگو برای حفظ زمینه. هر آیتم شامل `sender` ('user' یا 'bot') و `text` پیام است.

        **نکات**:
        - حداقل یکی از `message` یا `audio_data` باید ارائه شود.
        - تنظیمات چت‌بات (کلید API، دستورالعمل سیستمی) از مدل `BotSettings` یا متغیرهای محیطی خوانده می‌شود.
        - از مدل `gemini-2.5-flash` استفاده می‌کند.
        """,
        tags=['chat-bot'],
        request_body=ChatMessageSerializer,
        responses={
            200: openapi.Response(
                description="پاسخ چت‌بات با موفقیت دریافت شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'response': openapi.Schema(type=openapi.TYPE_STRING, description="متن پاسخ چت‌بات")}
                ),
                examples={"application/json": {"response": "سلام! چطور می‌توانم کمکتان کنم؟"}}
            ),
            400: openapi.Response(
                description="درخواست نامعتبر",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "پیام یا داده صوتی برای پردازش یافت نشد."}}
            ),
            500: openapi.Response(
                description="خطای سرور",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "تنظیمات بات یافت نشد."}}
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message_text = serializer.validated_data.get('message', '')
        audio_data_b64 = serializer.validated_data.get('audio_data')
        mime_type = serializer.validated_data.get('mime_type')
        conversation_history = serializer.validated_data.get('conversation_history', [])

        try:
            bot_settings = BotSettings.objects.first()
            if not bot_settings:
                return Response({"error": "تنظیمات بات یافت نشد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            google_api_key = bot_settings.google_api_key if bot_settings.google_api_key else os.environ.get('GEMINI_API_KEY')
            if not google_api_key:
                return Response({"error": "کلید API گوگل در تنظیمات یا متغیر محیطی GEMINI_API_KEY یافت نشد."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            configure(api_key=google_api_key)
            model = GenerativeModel(
                model_name='gemini-2.5-flash',
                safety_settings=safety_settings,
                system_instruction=bot_settings.system_instruction,
                tools=[Tool.google_search()]
            )

            chat_history = []
            for entry in conversation_history:
                sender = entry['sender']
                text = entry['text']
                if sender == 'user':
                    chat_history.append({'role': 'user', 'parts': [text]})
                elif sender == 'bot' and text:
                    chat_history.append({'role': 'model', 'parts': [text]})

            chat = model.start_chat(history=chat_history)

            current_message_parts = []
            if message_text:
                current_message_parts.append(message_text)
            if audio_data_b64 and mime_type:
                current_message_parts.append(Part.from_data(data=base64.b64decode(audio_data_b64), mime_type=mime_type))

            if not current_message_parts:
                return Response({"error": "پیام یا داده صوتی برای پردازش یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

            response_stream = chat.send_message_stream(current_message_parts)

            full_bot_response_text = ""
            for chunk in response_stream:
                if chunk.text:
                    full_bot_response_text += chunk.text

            return Response({"response": full_bot_response_text})

        except Exception as e:
            logger.exception("Error processing chatbot message:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotTTSView(APIView):
    @swagger_auto_schema(
        operation_summary="تبدیل متن به گفتار (Text-to-Speech)",
        operation_description="""
        این API یک متن را به عنوان ورودی دریافت کرده و فایل صوتی تبدیل شده به گفتار را برمی‌گرداند.
        از قابلیت TTS مدل Gemini 2.5 Flash استفاده می‌کند.

        **ورودی**:
        - `text` (الزامی): متنی که باید به گفتار تبدیل شود.

        **خروجی**:
        - `audio_data`: داده صوتی به صورت Base64.
        - `mime_type`: نوع MIME فایل صوتی (معمولاً `audio/x-flac`).

        **نکات**:
        - کلید API گوگل از `BotSettings` یا متغیر محیطی `GEMINI_API_KEY` خوانده می‌شود.
        - صدای پیش‌فرض بات از `bot_settings.default_voice` تعیین می‌شود.
        """,
        tags=['chat-bot'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='متنی که باید به گفتار تبدیل شود.')
            },
            example={"text": "سلام، چطور می‌توانم کمکتان کنم؟"}
        ),
        responses={
            200: openapi.Response(
                description="فایل صوتی با موفقیت تولید شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'audio_data': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BYTE, description="داده صوتی Base64"),
                        'mime_type': openapi.Schema(type=openapi.TYPE_STRING, description="نوع MIME فایل صوتی")
                    }
                ),
                examples={"application/json": {"audio_data": "base64_encoded_audio_data...", "mime_type": "audio/x-flac"}}
            ),
            400: openapi.Response(
                description="درخواست نامعتبر",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "متن برای تبدیل به گفتار فراهم نشده است."}}
            ),
            500: openapi.Response(
                description="خطای سرور",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "تنظیمات بات یافت نشد."}}
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        text_to_speak = request.data.get('text', '')
        if not text_to_speak:
            return Response({"error": "متن برای تبدیل به گفتار فراهم نشده است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bot_settings = BotSettings.objects.first()
            if not bot_settings:
                return Response({"error": "تنظیمات بات یافت نشد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            google_api_key = bot_settings.google_api_key if bot_settings.google_api_key else os.environ.get('GEMINI_API_KEY')
            if not google_api_key:
                return Response({"error": "کلید API گوگل در تنظیمات یا متغیر محیطی GEMINI_API_KEY یافت نشد."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            configure(api_key=google_api_key)
            model = GenerativeModel(model_name="gemini-2.5-flash-preview-tts")

            tts_response = model.generate_content(
                text_to_speak,
                generation_config=GenerationConfig(
                    response_modalities=[Modality.AUDIO],
                    speech_config=SpeechConfig(
                        voice_config={"prebuiltVoice": {"voiceName": bot_settings.default_voice}}
                    ),
                ),
            )
            
            audio_data_b64 = tts_response.candidates[0].content.parts[0].inline_data.data
            return Response({"audio_data": audio_data_b64, "mime_type": "audio/x-flac"})
            
        except Exception as e:
            logger.exception("Error during TTS generation:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotSettingsView(APIView):
    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات چت‌بات",
        operation_description="""
        این API تنظیمات کلی چت‌بات را برمی‌گرداند.
        این شامل دستورالعمل سیستمی، صدای پیش‌فرض، فعال بودن صدای بات، فونت‌های موجود و لینک‌های هتل (در صورت وجود) می‌شود.

        **خروجی**:
        - `system_instruction`: دستورالعمل سیستمی برای مدل چت‌بات.
        - `default_voice`: نام صدای پیش‌فرض برای تبدیل متن به گفتار.
        - `is_bot_voice_enabled`: آیا قابلیت گفتار برای بات فعال است یا خیر.
        - `available_fonts`: لیستی از فونت‌های موجود برای نمایش در چت.
        - `hotel_links`: لیستی از لینک‌های هتل (که احتمالا از `BotSettings` می‌آید).

        **نکات**:
        - اگر تنظیمات بات در دیتابیس یافت نشد، مقادیر پیش‌فرض منطقی برگردانده می‌شوند.
        """,
        tags=['chat-bot'],
        responses={
            200: openapi.Response(
                description="تنظیمات چت‌بات با موفقیت برگردانده شد.",
                schema=ChatSettingsSerializer,
                examples={"application/json": {
                    "system_instruction": "شما یک دستیار هوشمند هستید.",
                    "default_voice": "Kore",
                    "is_bot_voice_enabled": True,
                    "available_fonts": [{'name': 'وزیرمتن', 'family': 'Vazirmatn'}],
                    "hotel_links": [],
                }}
            ),
            500: openapi.Response(
                description="خطای سرور",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "خطا در دریافت تنظیمات چت‌بات."}}
            ),
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            bot_settings = BotSettings.objects.first()
            if not bot_settings:
                return Response({
                    "system_instruction": "شما یک دستیار هوشمند هستید.",
                    "default_voice": "Kore",
                    "is_bot_voice_enabled": True,
                    "available_fonts": [{'name': 'وزیرمتن', 'family': 'Vazirmatn'}],
                    "hotel_links": [],
                })
            
            serializer = ChatSettingsSerializer(bot_settings)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Error retrieving chatbot settings:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FAQListView(APIView):
    @swagger_auto_schema(
        operation_summary="لیست سوالات متداول (FAQ)",
        operation_description="""
        این API لیستی از سوالات متداول (FAQ) فعال را برمی‌گرداند.
        سوالات بر اساس ترتیب الفبایی مرتب شده و فقط موارد `is_active=True` نمایش داده می‌شوند.

        **مناسب برای**:
        - نمایش لیست سوالات متداول در بخش راهنما یا پشتیبانی چت‌بات.
        - ارائه گزینه‌های سریع به کاربر.
        """,
        tags=['chat-bot'],
        responses={
            200: openapi.Response(
                description="لیست سوالات متداول با موفقیت برگردانده شد.",
                schema=FAQSerializer(many=True),
                examples={"application/json": [
                    {"id": 1, "question": "ساعت کاری چت‌بات چه زمانی است؟", "answer": "24 ساعته در دسترس هستم."},
                    {"id": 2, "question": "چگونه می‌توانم هتل رزرو کنم؟", "answer": "لطفا نام هتل مورد نظر خود را بفرمایید."}
                ]}
            ),
            500: openapi.Response(
                description="خطای سرور",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                ),
                examples={"application/json": {"error": "خطا در دریافت لیست سوالات متداول."}}
            ),
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            faqs = FAQ.objects.filter(is_active=True).order_by('question')
            serializer = FAQSerializer(faqs, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Error retrieving FAQ list:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)