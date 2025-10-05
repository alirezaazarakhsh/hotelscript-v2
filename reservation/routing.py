from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/(?P<tracking_code>\w+)/$', consumers.ReservationConsumer.as_asgi()),
]
