import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from .models import Reservationhotel

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope['url_route']['kwargs']['tracking_code']
        self.group_name = f"reservation_{self.tracking_code}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        reservation = await self.get_reservation(self.tracking_code)

        if not reservation:
            await self.send_json({"status": "not_found", "timer": None})
            return

        # وضعیت لغو یا منقضی‌شده
        if reservation.status in ["cancelled", "expired"]:
            await self.send_json({"status": reservation.status, "timer": 0})
            return

        # pending_admin → تایمر واقعی
        if reservation.status == "pending_admin":
            remaining = await self.get_remaining_time(reservation)
            if remaining == 0:
                await self.expire_reservation(reservation)
                await self.send_json({"status": "expired", "timer": 0})
                return
            await self.send_json({"status": "pending_admin", "timer": int(remaining)})
            return

        # سایر وضعیت‌ها
        await self.send_json({"status": reservation.status, "timer": None})

    async def receive(self, text_data):
        """درخواست وضعیت فعلی از سمت کلاینت"""
        data = json.loads(text_data)
        action = data.get("action")

        if action == "get_status":
            reservation = await self.get_reservation(self.tracking_code)
            if not reservation:
                await self.send_json({"status": "not_found", "timer": 0})
                return

            remaining = (
                await self.get_remaining_time(reservation)
                if reservation.status == "pending_admin"
                else None
            )

            await self.send_json({
                "status": reservation.status,
                "timer": int(remaining) if remaining is not None else None
            })

    async def status_update(self, event):
        """دریافت بروزرسانی از سیگنال"""
        message = event["message"]
        status = message.get("status", "unknown")
        timer = message.get("timer")

        # اگر pending_admin باشد ولی تایمر نفرستاده → محاسبه کن
        if status == "pending_admin" and timer is None:
            reservation = await self.get_reservation(self.tracking_code)
            timer = await self.get_remaining_time(reservation)

        await self.send_json({
            "status": status,
            "timer": int(timer) if timer is not None else None
        })

    @sync_to_async
    def get_reservation(self, tracking_code):
        try:
            return Reservationhotel.objects.get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return None

    @sync_to_async
    def get_duration_minutes(self):
        """خواندن مدت زمان تایید از مدل ReservationApprovalDuration"""
        try:
            from reservation.models import ReservationApprovalDuration
            obj = ReservationApprovalDuration.objects.first()
            return obj.duration_minutes if obj else 5
        except Exception:
            return 5

    @sync_to_async
    def expire_reservation(self, reservation):
        reservation.status = "expired"
        reservation.save(update_fields=["status"])

    @sync_to_async
    def get_remaining_time(self, reservation):
        """محاسبه زمان باقی‌مانده بر اساس duration و timer_start"""
        duration_minutes = self.get_duration_minutes.sync()  # اجرای sync به صورت امن
        total_duration = duration_minutes * 60

        timer_start = getattr(reservation, "timer_start", None) or reservation.created_at
        elapsed = (timezone.now() - timer_start).total_seconds()
        return max(0, total_duration - elapsed)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))
