from django.contrib import admin
from .models import KavenegarSMSSetting, SMSPattern


class KavenegarSMSSettingInline(admin.TabularInline):
    model = KavenegarSMSSetting
    extra = 1
    verbose_name = "تنظیمات سامانه"
    verbose_name_plural = "تنظیمات سامانه‌ها"
    fields = ['name', 'api_token']


class SMSPatternInline(admin.TabularInline):
    model = SMSPattern
    extra = 1
    verbose_name = "پترن پیامک"
    verbose_name_plural = "پترن‌های پیامک"
    fields = ['name_fa', 'pattern_code']


@admin.register(KavenegarSMSSetting)
class KavenegarSMSSettingAdmin(admin.ModelAdmin):
    list_display = ['name', 'api_token']
    inlines = [SMSPatternInline]
    fieldsets = (
        ('تنظیمات سامانه', {
            'fields': ('name', 'api_token'),
        }),
    )

    def has_add_permission(self, request):
        # فقط اجازه اضافه کردن بده اگر هیچ تنظیماتی وجود نداشته باشد
        if KavenegarSMSSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(SMSPattern)
class SMSPatternAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}
