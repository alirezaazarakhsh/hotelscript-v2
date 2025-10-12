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
            return

        # تنظیم تایمر در لحظه اتصال به وب‌سوکت
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"

        if self.reservation.status == "pending_admin" and not cache.get(cache_key_approval):
            approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
            duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
            cache.set(cache_key_approval, timezone.now(), timeout=duration_seconds)
            print(f"Timer set for {self.tracking_code} (pending_admin): {duration_seconds} seconds")
        elif self.reservation.status == "confirmed" and not cache.get(cache_key_payment):
            cache.set(cache_key_payment, timezone.now(), timeout=1200)
            print(f"Timer set for {self.tracking_code} (confirmed): 1200 seconds")

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
                print(f"Reservation {self.tracking_code} not found, stopping loop")
                await self.send_json({"status": "not_found", "timer": 0})
                break

            status = self.reservation.status
            print(f"Checking status for {self.tracking_code}: {status}")

            if status in ["confirmed", "paid", "cancelled", "unconfirmed"]:
                print(f"Reservation {self.tracking_code} in final state: {status}, stopping loop")
                await self.send_json({"status": status, "timer": None})
                break

            remaining = 0
            show_timer = False

            if status == "pending_admin":
                start_time = cache.get(cache_key_approval)
                if start_time:
                    elapsed = (timezone.now() - start_time).total_seconds()
                    remaining = max(0, approval_duration_seconds - elapsed)
                    show_timer = True
                    print(f"Pending admin timer for {self.tracking_code}: {remaining} seconds remaining")
                    if remaining <= 0:
                        print(f"Timer expired for {self.tracking_code} (pending_admin), cancelling...")
                        await self.cancel_reservation(reason="approval_timeout")
                        # بررسی دوباره رزرو برای اطمینان از لغو
                        self.reservation = await self.get_reservation(self.tracking_code)
                        if self.reservation and self.reservation.status == "cancelled":
                            print(f"Reservation {self.tracking_code} successfully cancelled")
                            await self.send_json({"status": "cancelled", "timer": 0})
                            break
                        else:
                            print(f"Error: Failed to cancel {self.tracking_code}, current status: {self.reservation.status if self.reservation else 'not found'}")
                            await self.send_json({"status": status, "timer": 0})
                            break

            elif status == "confirmed":
                start_time = cache.get(cache_key_payment)
                if start_time:
                    elapsed = (timezone.now() - start_time).total_seconds()
                    remaining = max(0, payment_duration_seconds - elapsed)
                    show_timer = False
                    print(f"Confirmed timer for {self.tracking_code}: {remaining} seconds remaining")
                    if remaining <= 0:
                        print(f"Timer expired for {self.tracking_code} (confirmed), cancelling...")
                        await self.cancel_reservation(reason="payment_timeout")
                        # بررسی دوباره رزرو برای اطمینان از لغو
                        self.reservation = await self.get_reservation(self.tracking_code)
                        if self.reservation and self.reservation.status == "cancelled":
                            print(f"Reservation {self.tracking_code} successfully cancelled")
                            await self.send_json({"status": "cancelled", "timer": 0})
                            break
                        else:
                            print(f"Error: Failed to cancel {self.tracking_code}, current status: {self.reservation.status if self.reservation else 'not found'}")
                            await self.send_json({"status": status, "timer": 0})
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
            print(f"Reservation {tracking_code} not found in database")
            return None

    @sync_to_async
    def cancel_reservation(self, reason):
        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().filter(
                tracking_code=self.tracking_code
            ).first()
            if not reservation:
                print(f"Error: Reservation {self.tracking_code} not found for cancellation")
                return

            if reason == "approval_timeout" and reservation.status != "pending_admin":
                print(f"Error: Cannot cancel {self.tracking_code} for approval_timeout, current status: {reservation.status}")
                return
            if reason == "payment_timeout" and reservation.status != "confirmed":
                print(f"Error: Cannot cancel {self.tracking_code} for payment_timeout, current status: {reservation.status}")
                return

            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])
            print(f"Reservation {self.tracking_code} cancelled successfully")
            rooms = ReservationRoom.objects.filter(reservation=reservation).select_related('room')
            for r in rooms:
                room = Room.objects.select_for_update().get(pk=r.room.pk)
                is_auto_approved = reservation.status == 'confirmed'
                room.revert_inventory_for_cancellation(r.quantity, is_auto_approved)
                print(f"Inventory reverted for room {room.id}, quantity: {r.quantity}, auto_approved: {is_auto_approved}")
            
            # پاک کردن تایمرها از cache
            cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
            cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"
            cache.delete_many([cache_key_approval, cache_key_payment])
            print(f"Cache cleared for {self.tracking_code}")

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
        print(f"WebSocket disconnected for {self.tracking_code}")

    async def send_json(self, data):
        print(f"Sending message for {self.tracking_code}: {data}")
        await self.send(text_data=json.dumps(data))