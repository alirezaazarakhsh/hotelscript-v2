import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from .models import Reservationhotel, ReservationRoom, Room, ReservationApprovalDuration

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope["url_route"]["kwargs"]["tracking_code"]
        self.group_name = f"reservation_{self.tracking_code}"
        self.connected = True

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        self.reservation = await self.get_reservation(self.tracking_code)
        if not self.reservation:
            await self.send_json({"status": "not_found", "timer": 0})
            await self.close()
            return

        # تنظیم تایمر در لحظه اتصال به وب‌سوکت
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"

        if self.reservation.status == "pending_admin" and not cache.get(cache_key_approval):
            approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
            duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
            cache.set(cache_key_approval, timezone.now(), timeout=duration_seconds)
        elif self.reservation.status == "confirmed" and not cache.get(cache_key_payment):
            cache.set(cache_key_payment, timezone.now(), timeout=1200)

        asyncio.create_task(self.timer_loop())

    async def timer_loop(self):
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"
        approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
        approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
        payment_duration_seconds = 1200  # 20 دقیقه

        while self.connected:
            self.reservation = await self.get_reservation(self.tracking_code)
            if not self.reservation:
                await self.send_json({"status": "not_found", "timer": 0})
                await self.close()
                break

            status = self.reservation.status
            if status in ["paid", "cancelled", "unconfirmed"]:
                await self.send_json({"status": status, "timer": None})
                await self.close()
                break

            remaining = 0
            show_timer = False

            if status == "pending_admin":
                start_time = cache.get(cache_key_approval)
                if start_time:
                    elapsed = (timezone.now() - start_time).total_seconds()
                    remaining = max(0, approval_duration_seconds - elapsed)
                    show_timer = True
                    if remaining <= 0:
                        await self.cancel_reservation(reason="approval_timeout")
                        await self.send_json({"status": "cancelled", "timer": 0})
                        await self.close()
                        break

            elif status == "confirmed":
                start_time = cache.get(cache_key_payment)
                if start_time:
                    elapsed = (timezone.now() - start_time).total_seconds()
                    remaining = max(0, payment_duration_seconds - elapsed)
                    show_timer = False
                    if remaining <= 0:
                        await self.cancel_reservation(reason="payment_timeout")
                        await self.send_json({"status": "cancelled", "timer": 0})
                        await self.close()
                        break
                # برای confirmed بدون تایمر فعال، حلقه را متوقف می‌کنیم
                else:
                    await self.send_json({"status": status, "timer": None})
                    await self.close()
                    break

            await self.send_json({
                "status": status,
                "timer": int(remaining) if show_timer else None
            })

            await asyncio.sleep(1)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("action") == "get_status":
            remaining = await self.get_remaining_time()
            await self.send_json({
                "status": self.reservation.status,
                "timer": int(remaining) if self.reservation.status == "pending_admin" else None
            })

    @sync_to_async
    def get_reservation(self, tracking_code):
        try:
            return Reservationhotel.objects.get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return None

    @sync_to_async
    def cancel_reservation(self, reason):
        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().filter(
                tracking_code=self.tracking_code
            ).first()
            if not reservation:
                return

            if reason == "approval_timeout" and reservation.status != "pending_admin":
                return
            if reason == "payment_timeout" and reservation.status != "confirmed":
                return

            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])
            rooms = ReservationRoom.objects.filter(reservation=reservation).select_related('room')
            with transaction.atomic():
                for r in rooms:
                    room = Room.objects.select_for_update().get(pk=r.room.pk)
                    is_auto_approved = reservation.status == 'confirmed'
                    room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
            
            # پاک کردن تایمرها از cache
            cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
            cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"
            cache.delete_many([cache_key_approval, cache_key_payment])

    @sync_to_async
    def get_remaining_time(self):
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"
        approval_duration = ReservationApprovalDuration.objects.first()
        approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
        payment_duration_seconds = 1200

        if self.reservation.status == "pending_admin":
            start_time = cache.get(cache_key_approval)
            if start_time:
                elapsed = (timezone.now() - start_time).total_seconds()
                return max(0, approval_duration_seconds - elapsed)
        elif self.reservation.status == "confirmed":
            start_time = cache.get(cache_key_payment)
            if start_time:
                elapsed = (timezone.now() - start_time).total_seconds()
                return max(0, payment_duration_seconds - elapsed)
        return 0

    async def disconnect(self, close_code):
        self.connected = False
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def status_update(self, event):
        await self.send_json(event["message"])