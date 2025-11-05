import json
import base64
import logging
import os
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from google.generativeai import GenerativeModel, configure
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai
from google.cloud import texttospeech  # برای استفاده از Google Cloud TTS

from settingchatbot.models import BotSettings, FAQ
from .serializers import ChatMessageSerializer, ChatSettingsSerializer, FAQSerializer

# For Swagger documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

logger = logging.getLogger(__name__)

# Safety settings
safety_settings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]

class ChatbotMessageView(APIView):
    permission_classes = [AllowAny]
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
            )

            # Build chat history
            chat = model.start_chat(history=[])
            
            # Add conversation history to the chat
            for entry in conversation_history:
                if entry['sender'] == 'user':
                    chat.history.append({
                        'role': 'user',
                        'parts': [entry['text']]
                    })
                elif entry['sender'] == 'bot':
                    chat.history.append({
                        'role': 'model',
                        'parts': [entry['text']]
                    })

            # Prepare current message parts
            current_message_parts = []
            if message_text:
                current_message_parts.append(message_text)
            if audio_data_b64 and mime_type:
                audio_bytes = base64.b64decode(audio_data_b64)
                current_message_parts.append({
                    'mime_type': mime_type,
                    'data': audio_bytes
                })

            if not current_message_parts:
                return Response({"error": "پیام یا داده صوتی برای پردازش یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

            # Send message and get response
            if len(current_message_parts) == 1 and isinstance(current_message_parts[0], str):
                # Text only message
                response = chat.send_message(current_message_parts[0])
            else:
                # Mixed content (text + audio)
                response = chat.send_message(current_message_parts)

            full_bot_response_text = response.text

            return Response({"response": full_bot_response_text})

        except Exception as e:
            logger.exception("Error processing chatbot message:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotTTSView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        operation_summary="تبدیل متن به گفتار (Text-to-Speech)",
        operation_description="""
        این API یک متن را به عنوان ورودی دریافت کرده و فایل صوتی تبدیل شده به گفتار را برمی‌گرداند.
        از Google Cloud Text-to-Speech API استفاده می‌کند.

        **ورودی**:
        - `text` (الزامی): متنی که باید به گفتار تبدیل شود.
        - `voice_name` (اختیاری): نام صدای دستیار (مثل 'Kore' یا 'Puck').

        **خروجی**:
        - `audio_data`: داده صوتی به صورت Base64.
        - `mime_type`: نوع MIME فایل صوتی (مثل 'audio/mp3').

        **نکات**:
        - کلید API گوگل از `BotSettings` یا متغیر محیطی `GEMINI_API_KEY` خوانده می‌شود.
        - صدای پیش‌فرض بات از `bot_settings.default_voice` تعیین می‌شود.
        - این API با دستیارهای صوتی گوگل (Google Cloud TTS) ادغام شده است.
        """,
        tags=['chat-bot'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='متنی که باید به گفتار تبدیل شود.'),
                'voice_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام صدای دستیار (اختیاری).')
            },
            example={"text": "سلام، چطور می‌توانم کمکتان کنم؟", "voice_name": "Kore"}
        ),
        responses={
            200: openapi.Response(
                description="فایل صوتی با موفقیت تولید شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'audio_data': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BASE64, description="داده صوتی Base64"),
                        'mime_type': openapi.Schema(type=openapi.TYPE_STRING, description="نوع MIME فایل صوتی")
                    }
                ),
                examples={"application/json": {"audio_data": "base64_encoded_audio_data...", "mime_type": "audio/mp3"}}
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
        voice_name = request.data.get('voice_name', None)  # اختیاری از فرانت
        if not text_to_speak:
            return Response({"error": "متن برای تبدیل به گفتار فراهم نشده است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bot_settings = BotSettings.objects.first()
            if not bot_settings:
                return Response({"error": "تنظیمات بات یافت نشد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # استفاده از صدای پیش‌فرض اگر voice_name ارسال نشده باشد
            if not voice_name:
                voice_name = bot_settings.default_voice

            # تنظیم کلاینت Google Cloud TTS (نیاز به credentials.json یا env var GOOGLE_APPLICATION_CREDENTIALS)
            client = texttospeech.TextToSpeechClient()

            # تنظیم ورودی متن
            synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)

            # تنظیم صدا (voice_name باید با فرمت Google TTS سازگار باشد، مثل 'fa-IR-Wavenet-A' برای فارسی)
            voice = texttospeech.VoiceSelectionParams(
                language_code="fa-IR",  # برای فارسی، یا بر اساس voice_name تغییر دهید
                name=voice_name,  # استفاده از voice_name (مثل 'Kore' یا 'Puck' اگر ساپورت شود، اما Google TTS نام‌های خاص خودش رو داره)
            )

            # تنظیم فرمت خروجی (مثل MP3)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # درخواست TTS
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # تبدیل audio_content به base64
            audio_data_b64 = base64.b64encode(response.audio_content).decode('utf-8')
            mime_type = "audio/mp3"

            return Response({
                "audio_data": audio_data_b64, 
                "mime_type": mime_type
            })

        except Exception as e:
            logger.exception("Error during TTS generation:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotSettingsView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات چت‌بات",
        operation_description="""
        این API تنظیمات کلی چت‌بات را برمی‌گرداند.
        این شامل دستورالعمل سیستمی، صدای پیش‌فرض، فعال بودن صدای بات، فونت‌های موجود می‌شود.

        **خروجی**:
        - `system_instruction`: دستورالعمل سیستمی برای مدل چت‌بات.
        - `default_voice`: نام صدای پیش‌فرض برای تبدیل متن به گفتار.
        - `is_bot_voice_enabled`: آیا قابلیت گفتار برای بات فعال است یا خیر.
        - `available_fonts`: لیستی از فونت‌های موجود برای نمایش در چت.
        - `welcome_title`: عنوان خوش‌آمدگویی.
        - `welcome_message`: پیام خوش‌آمدگویی.
        - `logo_url`: URL لوگو (اگر موجود باشد).

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
                    "welcome_title": "چت بات هوشمند سفرنامه ۲۴",
                    "welcome_message": "به چت بات هوشمند سفرنامه ۲۴ خوش آمدید.",
                    "logo_url": "https://example.com/logo.png",
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
                    "welcome_title": "چت بات هوشمند سفرنامه ۲۴",
                    "welcome_message": "به چت بات هوشمند سفرنامه ۲۴ خوش آمدید. اگر نیاز به مشاوره قبل از خرید یا انتخاب دارید، این چت بات نیاز شما را برطرف می‌کند. لطفا safarnameh24.com را دنبال کنید.",
                    "logo_url": "http://cps.safarnameh24.com/media/images/logo/full-red-gray_mej9jEE.webp",
                })
            
            serializer = ChatSettingsSerializer(bot_settings, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Error retrieving chatbot settings:")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FAQListView(APIView):
    permission_classes = [AllowAny]
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