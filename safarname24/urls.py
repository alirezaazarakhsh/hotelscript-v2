"""
URL configuration for safarname24 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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
        description="API SAFARNAMEH",
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
        path('profile/', include('user_profile.urls', namespace='profile')),
        path('icons/', include('icons.urls', namespace='icons')),
        path('setting_sms/', include('setting_sms.urls', namespace='setting_sms')),
        path('profile/', include([
            path(
                'passengers/',
                reservation_views.PassengerListCreateView.as_view(),
                name='passenger-list-create'
            ),
        ])),
    ])),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls"))
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

