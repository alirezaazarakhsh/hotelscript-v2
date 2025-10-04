import os
from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from .consumer import MyConsumer


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safarname24.settings')
 
# application = get_asgi_application()


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": 
            URLRouter(
                [
                    path("ws/websocket/", MyConsumer.as_asgi()),
                ]
            )
        
    }
)