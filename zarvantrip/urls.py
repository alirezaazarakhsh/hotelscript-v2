from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from reservation import views as reservation_views
from authentication.admin_forms import AdminOTPAuthenticationForm


# ------------------------------------------------------------------------------
# هندلر اختصاصی 404 برای بازگرداندن JSON به جای صفحه زشت HTML
# ------------------------------------------------------------------------------
def custom_404_view(request, exception=None):
    return JsonResponse({
        "message": "آدرس مورد نظر در سرور یافت نشد (404).",
        "data": {},
        "success": False
    }, status=404)

handler404 = custom_404_view


# Configure admin site to use custom login form
admin.site.login_form = AdminOTPAuthenticationForm
admin.site.login_template = 'admin/login.html'

schema_view = get_schema_view(
    openapi.Info(
        title="API SITE HOTEL",
        default_version='v1',
        description="API ZARVANTRIP",
        terms_of_service="https://www.sevinhost.com/",
        contact=openapi.Contact(email="alirezaazarakhsh20@gmail.com"),
        license=openapi.License(name="checked ✅"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Empty schema for adminpanel ReDoc (shows no endpoints)
schema_view_adminpanel_empty = get_schema_view(
    openapi.Info(
        title="API ADMIN HOTEL",
        default_version='v1',
        description="API ZARVANTRIP",
        terms_of_service="https://www.sevinhost.com/",
        contact=openapi.Contact(email="alirezaazarakhsh20@gmail.com"),
        license=openapi.License(name="checked ✅"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[],
)

urlpatterns = [
    # تنظیم لینک بک اند وب سایت و پنل ادمین جنگو
    path('admin/', admin.site.urls),
    
    # APIهای سایت (برای کاربران/وب‌سایت)
    path('api/v1/', include([
        path('', include('authentication.urls', namespace='auth')),
        path('config/', include('config.urls', namespace='config')),
        path('contact/', include('contact.urls', namespace='contact')),
        path('blog/', include('blog.urls', namespace='blog')),
        
        # پشتیبانی همزمان از هر دو مسیر hotel و best-hotels برای جلوگیری از ارور 404
        path('hotel/', include('reservation.urls', namespace='reservation')),
        path('best-hotels/', include('reservation.urls')),
        path('hotels/', include('reservation.urls')),
        
        path('finance/', include('finance.urls', namespace='finance')),
        path('icons/', include('icons.urls', namespace='icons')),
        path('setting_sms/', include('setting_sms.urls', namespace='setting_sms')),
        path('notification/', include('notification.urls', namespace='notification')),
        path('crm/', include('bashgah_moshtarian.urls', namespace='bashgah')), 
        path('favorite/', include('favorite.urls', namespace='favorites')),
        path('payment/', include('setting_payment.urls', namespace='payment')),
        
        # --- URL های چت بات و تنظیمات جدید ---
        path('subscription/', include('user_subscription_settings.urls', namespace='subscription')),
    ])),
    
    # APIهای پنل گرافیکی (برای تنظیمات/ادمین)
    path('api/v1/adminpanel/', include([
        
    ])),
    
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('redoc/adminpanel', schema_view_adminpanel_empty.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path('_nested_admin/', include('nested_admin.urls')),  # 👈 این خط برای کارکرد دکمه‌های افزودن الزامی است

    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)