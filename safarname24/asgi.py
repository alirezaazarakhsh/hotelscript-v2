import os
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from .consumer import MyConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safarnameh24.settings')

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter([
                path("ws/websocket/", MyConsumer.as_asgi()),
            ])
        ),
    }
)
