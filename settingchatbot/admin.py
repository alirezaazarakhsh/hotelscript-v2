from django.contrib import admin
from .models import BotSettings, FAQ  # اگر FAQ هم داری، import کن؛ اگر نه، حذفش کن

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """
    ادمین برای تنظیمات بات. فقط اجازه اضافه کردن یک رکورد رو می‌ده (singleton).
    """
    list_display = ('default_voice', 'is_bot_voice_enabled', 'google_api_key')  # فیلدهای نمایش در لیست
    fieldsets = (
        ('تنظیمات اصلی', {
            'fields': ('google_api_key', 'system_instruction', 'default_voice', 'is_bot_voice_enabled'),
        }),
        ('تنظیمات اضافی', {
            'fields': ('available_fonts', 'hotel_links'),
        }),
    )
    # فقط اگر هیچ رکوردی نبود، اجازه اضافه کردن بده (singleton)
    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

# اگر مدل FAQ داری، این رو اضافه کن
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    ادمین برای سوالات متداول (FAQ).
    """
    list_display = ('question', 'is_active', 'created_at', 'updated_at')
    search_fields = ('question', 'answer')
    list_filter = ('is_active',)
    ordering = ['-created_at']
    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'is_active'),
        }),
    )