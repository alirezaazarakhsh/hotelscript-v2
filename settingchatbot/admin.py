from django.contrib import admin
from .models import BotSettings, FAQ

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """
    ادمین برای تنظیمات بات. فقط اجازه اضافه کردن یک رکورد رو می‌ده (singleton).
    """
    # فیلدهای نمایش در لیست: available_fonts و hotel_links حذف شدند
    list_display = ('default_voice', 'is_bot_voice_enabled', 'google_api_key') 
    fieldsets = (
        ('تنظیمات اصلی', {
            # available_fonts و hotel_links از اینجا حذف شدند
            'fields': ('google_api_key', 'system_instruction', 'default_voice', 'is_bot_voice_enabled'),
        }),
        # 'تنظیمات اضافی' که شامل available_fonts و hotel_links بود، حذف شد
    )
    
    # فقط اگر هیچ رکوردی نبود، اجازه اضافه کردن بده (singleton)
    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    ادمین برای سوالات متداول (FAQ).
    """
    # created_at و updated_at از list_display حذف شدند
    list_display = ('question', 'is_active')
    search_fields = ('question', 'answer')
    list_filter = ('is_active',)
    # created_at از ordering حذف شد. می‌توانید بر اساس 'question' مرتب‌سازی کنید یا این خط را حذف کنید.
    ordering = ['question'] # مرتب‌سازی بر اساس سوال به ترتیب الفبا
    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'is_active'),
        }),
    )