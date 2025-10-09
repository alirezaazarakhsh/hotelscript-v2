import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from .models import Reservationhotel, ReservationRoom, ReservationApprovalDuration

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope['url_route']['kwargs']['tracking_code']
        self.group_name = f"reservation_{self.tracking_code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        self.reservation = await self.get_reservation(self.tracking_code)

        if not self.reservation:
            await self.send_json({"status": "not_found", "timer": 0})
            return

        if self.reservation.status == "pending_admin":
            await self.start_timer_loop()
        else:
            await self.send_json({"status": self.reservation.status, "timer": None})

    async def start_timer_loop(self):
        cache_key = f"reservation_timer_{self.tracking_code}"
        start_time = cache.get(cache_key)
        approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
        duration_minutes = approval_duration.duration_minutes if approval_duration else 5

        if not start_time:
            start_time = timezone.now()
            cache.set(cache_key, start_time, timeout=duration_minutes * 60)

        while True:
            elapsed = (timezone.now() - start_time).total_seconds()
            remaining = max(0, duration_minutes * 60 - elapsed)
            if remaining <= 0:
                await self.cancel_reservation()
                await self.send_json({"status": "cancelled", "timer": 0})
                break
            await self.send_json({"status": "pending_admin", "timer": int(remaining)})
            await asyncio.sleep(1)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("action") == "get_status":
            remaining = await self.get_remaining_time()
            await self.send_json({
                "status": self.reservation.status,
                "timer": int(remaining) if remaining else 0
            })

    @sync_to_async
    def get_reservation(self, tracking_code):
        try:
            return Reservationhotel.objects.get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return None

    @sync_to_async
    def cancel_reservation(self):
        self.reservation.status = "cancelled"
        self.reservation.save(update_fields=["status"])
        rooms = ReservationRoom.objects.filter(reservation=self.reservation)
        for r in rooms:
            room = r.room
            room.inventory += r.quantity
            if not room.auto_approval:
                room.count += r.quantity
            room.save(update_fields=['inventory', 'count', 'auto_approved_count'])
        cache.delete(f"reservation_timer_{self.tracking_code}")

    @sync_to_async
    def get_remaining_time(self):
        cache_key = f"reservation_timer_{self.tracking_code}"
        start_time = cache.get(cache_key)
        if not start_time:
            return 0
        approval_duration = ReservationApprovalDuration.objects.first()
        duration_minutes = approval_duration.duration_minutes if approval_duration else 5
        elapsed = (timezone.now() - start_time).total_seconds()
        return max(0, duration_minutes * 60 - elapsed)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))
