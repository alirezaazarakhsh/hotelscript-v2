import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "zarvantrip.settings"
)


# راه‌اندازی Django قبل از import کردن routing
django_asgi_app = get_asgi_application()


def websocket_application():
    from reservation.routing import websocket_urlpatterns

    return AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,

        "websocket": websocket_application(),
    }
)