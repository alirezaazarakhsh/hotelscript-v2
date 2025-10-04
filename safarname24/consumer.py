import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class MyConsumer(WebsocketConsumer):
    def connect(self):
        # اتصال به گروه "reservation_notifications"
        async_to_sync(self.channel_layer.group_add)(
            "reservation_notifications",  # نام گروه
            self.channel_name
        )
        self.accept()
        self.send(text_data=json.dumps({"message": "You are connected!"}))
        

    def disconnect(self, close_code):
        # حذف از گروه هنگام قطع اتصال
        async_to_sync(self.channel_layer.group_discard)(
            "reservation_notifications",
            self.channel_name
        )

    def receive(self, text_data):
        # دریافت پیام از کلاینت
        print("Received data:", text_data)
        self.send(text_data="thanks")

    def status_update(self, event):
        # ارسال پیام به کلاینت وقتی وضعیت رزرو تغییر کرد
        self.send(text_data=json.dumps({
            "message": event["message"]
        }))

