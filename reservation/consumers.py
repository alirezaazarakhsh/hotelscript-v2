import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from .models import Reservationhotel, ReservationRoom, Room, ReservationApprovalDuration
import logging

logger = logging.getLogger(__name__)

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope["url_route"]["kwargs"]["tracking_code"]
        self.group_name = f"reservation_{self.tracking_code}"
        self.connected = True

        logger.info(f"Connecting to WebSocket with tracking_code: {self.tracking_code}")

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        self.reservation = await self.get_reservation(self.tracking_code)
        if not self.reservation:
            logger.error(f"Reservation {self.tracking_code} not found on connect")
            await self.send_json({"capacity_status": "not_found", "timer": 0})
            return
        # قبلاً تایمر به محض اتصال شروع می‌شد؛ حالا تایمر تنها وقتی که فرانت با عمل
        # `start_approval_timer` درخواست کند شروع خواهد شد. loop نمایش وضعیت مصرف‌کننده را ادامه می‌دهد.
        asyncio.create_task(self.timer_loop())

    async def timer_loop(self):
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
        approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300

        while self.connected:
            self.reservation = await self.get_reservation(self.tracking_code)
            if not self.reservation:
                logger.error(f"Reservation {self.tracking_code} not found in timer_loop")
                await self.send_json({"capacity_status": "not_found", "timer": 0})
                break

            capacity_status = self.reservation.capacity_status
            logger.debug(f"Checking capacity_status for {self.tracking_code}: {capacity_status}")

            if capacity_status in ["confirmed", "rejected"]:
                logger.info(f"Reservation {self.tracking_code} in final state: {capacity_status}")
                await self.send_json({"capacity_status": capacity_status, "timer": None})
                break

            remaining = 0
            show_timer = False

            if capacity_status == "pending":
                # بررسی کنیم آیا تایمر approval در cache ست شده است (مقدار expiry به صورت epoch timestamp ذخیره می‌شود)
                cache_value = cache.get(cache_key_approval)
                if cache_value:
                    try:
                        expires_at_ts = float(cache_value)
                        remaining = max(0, expires_at_ts - timezone.now().timestamp())
                        show_timer = True
                        logger.debug(f"Pending timer for {self.tracking_code}: {remaining} seconds remaining (cache_expiry_ts={expires_at_ts})")
                        if remaining <= 0:
                            logger.info(f"Timer expired for {self.tracking_code} (pending) according to cache expiry, rejecting...")
                            await self.reject_reservation(reason="approval_timeout")
                            self.reservation = await self.get_reservation(self.tracking_code)
                            if self.reservation and self.reservation.capacity_status == "rejected":
                                logger.info(f"Reservation {self.tracking_code} successfully rejected")
                                await self.send_json({"capacity_status": "rejected", "timer": None})
                                break
                            else:
                                logger.error(f"Error: Failed to reject {self.tracking_code}, current capacity_status: {self.reservation.capacity_status if self.reservation else 'not found'}")
                                await self.send_json({"capacity_status": capacity_status, "timer": None})
                                break
                    except Exception:
                        logger.exception(f"Invalid cache value for {cache_key_approval}: {cache_value}")
                else:
                    # هنوز تایمر توسط کلاینت شروع نشده؛ اما برای جلوگیری از مخفی شدن تایمر، مقدار کامل duration را به فرانت نشان می‌دهیم
                    remaining = approval_duration_seconds
                    show_timer = True
                    logger.debug(f"Pending state without started timer for {self.tracking_code}; showing full duration {remaining}s until front starts timer")

            await self.send_json({
                "capacity_status": capacity_status,
                "timer": int(remaining) if show_timer else None
            })

            await asyncio.sleep(1)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        if action == "get_status":
            remaining = await self.get_remaining_time()
            await self.send_json({
                "capacity_status": self.reservation.capacity_status,
                "timer": int(remaining) if self.reservation.capacity_status == "pending" else None
            })
        elif action == "start_approval_timer":
            # شروع دستی تایمر: expiry را در cache ست می‌کنیم (به همراه timeout برابر duration)
            approval_duration = await sync_to_async(ReservationApprovalDuration.objects.first)()
            approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300
            cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"

            if not cache.get(cache_key_approval):
                expires_at_ts = timezone.now().timestamp() + approval_duration_seconds
                # ذخیره مقدار expiry به عنوان عدد (epoch) و ست کردن timeout تا خودش پاک شود
                cache.set(cache_key_approval, str(expires_at_ts), timeout=approval_duration_seconds)
                logger.info(f"Manual approval timer start (cache) for {self.tracking_code}: expires_at_ts={expires_at_ts} ({approval_duration_seconds}s)")
            else:
                logger.info(f"Manual start ignored; timer already exists for {self.tracking_code}")

            remaining = await self.get_remaining_time()
            await self.send_json({
                "capacity_status": self.reservation.capacity_status,
                "timer": int(remaining) if self.reservation.capacity_status == "pending" else None
            })

    @sync_to_async
    def get_reservation(self, tracking_code):
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
            logger.debug(f"Reservation found for {tracking_code}: capacity_status={reservation.capacity_status}")
            return reservation
        except Reservationhotel.DoesNotExist:
            logger.error(f"Reservation {tracking_code} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error fetching reservation {tracking_code}: {str(e)}")
            return None

    def _set_reservation_expiry(self, expires_at):
        # legacy placeholder (no-op) — kept to avoid breaking callers that may exist elsewhere
        return False

    @sync_to_async
    def reject_reservation(self, reason):
        with transaction.atomic():
            reservation = Reservationhotel.objects.select_for_update().filter(
                tracking_code=self.tracking_code
            ).first()
            if not reservation:
                logger.error(f"Error: Reservation {self.tracking_code} not found for rejection")
                return

            if reason == "approval_timeout" and reservation.capacity_status != "pending":
                logger.error(f"Error: Cannot reject {self.tracking_code} for approval_timeout, current capacity_status: {reservation.capacity_status}")
                return

            # فقط وضعیت را تغییر می‌دهیم، signal خودش موجودی را برمی‌گرداند
            reservation.capacity_status = "rejected"
            reservation.save(update_fields=["capacity_status"])
            logger.info(f"Reservation {self.tracking_code} rejected, inventory will be reverted by signal")

            cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
            cache_key_payment = f"reservation_payment_timer_{self.tracking_code}"
            cache.delete_many([cache_key_approval, cache_key_payment])
            logger.debug(f"Cache cleared for {self.tracking_code}")

    @sync_to_async
    def get_remaining_time(self):
        cache_key_approval = f"reservation_approval_timer_{self.tracking_code}"
        approval_duration = ReservationApprovalDuration.objects.first()
        approval_duration_seconds = approval_duration.duration_minutes * 60 if approval_duration else 300

        if self.reservation.capacity_status == "pending":
            cache_value = cache.get(cache_key_approval)
            if cache_value:
                try:
                    expires_at_ts = float(cache_value)
                    remaining = expires_at_ts - timezone.now().timestamp()
                    return max(0, remaining)
                except Exception:
                    logger.exception(f"Invalid cache value for {cache_key_approval}: {cache_value}")
            # اگر تایمر هنوز توسط فرانت شروع نشده، برای جلوگیری از مخفی شدن، مدت کامل را نشان بده
            return approval_duration_seconds
        return 0

    async def disconnect(self, close_code):
        self.connected = False
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"WebSocket disconnected for {self.tracking_code}")

    async def send_json(self, data):
        logger.debug(f"Sending message for {self.tracking_code}: {data}")
        await self.send(text_data=json.dumps(data))

    async def status_update(self, event):
        logger.debug(f"Status update received for {self.tracking_code}: {event['message']}")
        await self.send_json(event["message"])