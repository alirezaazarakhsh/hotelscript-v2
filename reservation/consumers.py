import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope['url_route']['kwargs']['tracking_code']
        self.group_name = f"reservation_{self.tracking_code}"

        # اضافه کردن به گروه
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # خروج از گروه
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def status_update(self, event):
        # ارسال پیام به کلاینت
        await self.send(text_data=json.dumps(event['message']))