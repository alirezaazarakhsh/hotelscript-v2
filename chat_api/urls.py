# chat_api/urls.py
from django.urls import path
from .views import ChatbotMessageView, ChatbotTTSView, ChatbotSettingsView, FAQListView # FAQListView را ایمپورت کنید

app_name = 'chat_api'

urlpatterns = [
    path('message/', ChatbotMessageView.as_view(), name='chatbot_message'),
    path('tts/', ChatbotTTSView.as_view(), name='chatbot_tts'),
    path('settings/', ChatbotSettingsView.as_view(), name='chatbot_settings'),
    path('faqs/', FAQListView.as_view(), name='chatbot_faqs'), # این خط را اضافه کنید
]