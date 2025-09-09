from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from reservation import views as reservation_views

schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version='v1',
        description="API SAFARNAMEH24",
        terms_of_service="https://www.sevinhost.com/",
        contact=openapi.Contact(email="alirezaazarakhsh20@gmail.com"),
        license=openapi.License(name="checked ✅"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('', include('authentication.urls', namespace='auth')),
        path('config/', include('config.urls', namespace='config')),
        path('contact/', include('contact.urls', namespace='contact')),
        path('blog/', include('blog.urls', namespace='blog')),
        path('hotel/', include('reservation.urls', namespace='reservation')),
        path('finance/', include('finance.urls', namespace='finance')),
        path('icons/', include('icons.urls', namespace='icons')),
        path('setting_sms/', include('setting_sms.urls', namespace='setting_sms')),
        path('notification/', include('notification.urls', namespace='notification')),
        path('crm/', include('bashgah_moshtarian.urls', namespace='bashgah')), 
        path('favorite/', include('favorite.urls', namespace='favorites')),

    ])),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls"))
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

   # مسیر بکاپ فایل ها مدیا در ربت 
    urlpatterns += static('/sf24_9xkLp7/', document_root='/var/backups/sf24_9xkLp7/')