import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class MyConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            # اجازه اتصال به ناشناس‌ها ندیم
            self.close()
        else:
            # گروه اختصاصی برای هر کاربر
            self.group_name = f"reservation_user_{user.id}"
            async_to_sync(self.channel_layer.group_add)(
                self.group_name,
                self.channel_name
            )
            self.accept()
            self.send(text_data=json.dumps({"message": "You are connected!"}))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            getattr(self, "group_name", None),
            self.channel_name
        )

    def receive(self, text_data):
        # این پروژه فقط ارسال وضعیت از سرور به کلاینت است
        pass

    def status_update(self, event):
        # ارسال پیام به کلاینت
        self.send(text_data=json.dumps(event["message"]))
