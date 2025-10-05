from django.urls import re_path
from .consumers import ReservationConsumer

websocket_urlpatterns = [
    re_path(r'ws/(?P<tracking_code>\w+)/$', consumers.ReservationConsumer.as_asgi()),
]
