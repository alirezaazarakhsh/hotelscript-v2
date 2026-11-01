import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from hotel_bot.config import BOT_TOKEN, SUPER_ADMINS
from .models import (
    Reservationhotel,
    ReservationRoom,
    Room,
    ReservationApprovalDuration,
)

logger = logging.getLogger(__name__)


class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope["url_route"]["kwargs"]["tracking_code"]
        self.group_name = f"reservation_{self.tracking_code}"
        self.connected = True

        logger.info(f"Connecting to WebSocket: tracking_code={self.tracking_code}")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        self.reservation = await self.get_reservation(self.tracking_code)
        if not self.reservation:
            await self.send_json({"capacity_status": "not_found", "timer": None, "wallet_balance": 0})
            return

        asyncio.create_task(self.timer_loop())

    async def timer_loop(self):
        approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
        approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"

        while self.connected:
            self.reservation = await self.get_reservation(self.tracking_code)
            if not self.reservation:
                break

            capacity_status = self.reservation.capacity_status
            payment_status = self.reservation.payment_status

            # استخراج زنده موجودی کیف پول خریدار
            wallet_balance = await sync_to_async(
                lambda: int(self.reservation.buyer.wallet.balance) if hasattr(self.reservation.buyer, 'wallet') and self.reservation.buyer.wallet else 0
            )()

            # اگر رزرو تایید شد (چه توسط ادمین در پنل جنگو و چه توسط اسنپ)
            if capacity_status == "confirmed":
                timer_val = 900 if payment_status != "paid" else None
                await self.send_json({
                    "capacity_status": "confirmed",
                    "payment_status": payment_status,
                    "snapp_status": self.reservation.snapp_status,
                    "wallet_balance": wallet_balance,
                    "timer": timer_val
                })
                break

            elif capacity_status == "rejected":
                await self.send_json({
                    "capacity_status": "rejected",
                    "payment_status": payment_status,
                    "snapp_status": self.reservation.snapp_status,
                    "wallet_balance": wallet_balance,
                    "timer": None
                })
                break

            # وضعیت Pending (در انتظار بررسی ظرفیت)
            remaining = approval_duration_seconds
            cache_value = cache.get(cache_key_approval)
            if cache_value:
                try:
                    expires_at_ts = float(cache_value)
                    remaining = max(0, expires_at_ts - timezone.now().timestamp())
                    if remaining <= 0:
                        await self.reject_reservation(reason="approval_timeout")
                        await self.send_json({
                            "capacity_status": "rejected",
                            "payment_status": payment_status,
                            "wallet_balance": wallet_balance,
                            "timer": None
                        })
                        break
                except Exception:
                    pass

            await self.send_json({
                "capacity_status": "pending",
                "payment_status": payment_status,
                "snapp_status": self.reservation.snapp_status,
                "wallet_balance": wallet_balance,
                "timer": int(remaining)
            })

            await asyncio.sleep(2)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        self.reservation = await self.get_reservation(self.tracking_code)
        wallet_balance = await sync_to_async(
            lambda: int(self.reservation.buyer.wallet.balance) if hasattr(self.reservation.buyer, 'wallet') and self.reservation.buyer.wallet else 0
        )()

        if action == "get_status":
            remaining = 900 if self.reservation.capacity_status == "confirmed" else approval_duration_seconds
            await self.send_json({
                "capacity_status": self.reservation.capacity_status,
                "payment_status": self.reservation.payment_status,
                "snapp_status": self.reservation.snapp_status,
                "wallet_balance": wallet_balance,
                "timer": remaining
            })
        elif action == "start_approval_timer":
            approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
            approval_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
            cache_key = f"reservation_approval_timer_{self.tracking_code}"
            now_ts = timezone.now().timestamp()
            cache.set(cache_key, str(now_ts + approval_seconds), timeout=approval_seconds)

            await self.send_json({
                "capacity_status": self.reservation.capacity_status,
                "payment_status": self.reservation.payment_status,
                "wallet_balance": wallet_balance,
                "timer": approval_seconds
            })

    @sync_to_async
    def get_reservation(self, tracking_code):
        try:
            return Reservationhotel.objects.select_related('buyer').get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return None

    @sync_to_async
    def reject_reservation(self, reason):
        with transaction.atomic():
            res = Reservationhotel.objects.select_for_update().filter(tracking_code=self.tracking_code).first()
            if res and res.capacity_status == "pending":
                res.capacity_status = "rejected"
                res.save(update_fields=["capacity_status"])

    async def disconnect(self, close_code):
        self.connected = False
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def status_update(self, event):
        await self.send_json(event["message"])