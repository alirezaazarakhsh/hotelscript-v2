import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Reservationhotel

class ReservationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tracking_code = self.scope['url_route']['kwargs']['tracking_code']
        self.group_name = f"reservation_{self.tracking_code}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # ارسال وضعیت اولیه رزرو
        try:
            reservation = Reservationhotel.objects.get(tracking_code=self.tracking_code)
            duration_minutes = None
            timer_start = None
            if reservation.status == 'pending_admin':
                try:
                    from reservation.models import ReservationApprovalDuration
                    approval_duration = ReservationApprovalDuration.objects.first()
                    duration_minutes = approval_duration.duration_minutes if approval_duration else 5
                except Exception as e:
                    duration_minutes = 5
                timer_start = reservation.created_at.isoformat() if reservation.created_at else timezone.now().isoformat()

            await self.send(text_data=json.dumps({
                "status": reservation.status,
                "duration_minutes": duration_minutes,
                "timer_start": timer_start,
            }))
        except Reservationhotel.DoesNotExist:
            await self.send(text_data=json.dumps({
                "status": "not_found",
                "message": "رزرو با این کد پیگیری یافت نشد.",
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def status_update(self, event):
        await self.send(text_data=json.dumps(event['message']))