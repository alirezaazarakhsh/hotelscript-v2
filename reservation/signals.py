from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F

from reservation.models import ReservationRoom

# وقتی رزرو اتاق ساخته یا ویرایش شد
@receiver(post_save, sender=ReservationRoom)
def update_room_inventory_on_save(sender, instance, created, **kwargs):
    room = instance.room
    # جمع تعداد رزرو شده برای این اتاق
    total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
    # موجودی جدید = موجودی اولیه - مجموع رزروها
    room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
    # فقط فیلد inventory رو به‌روزرسانی کن
    room.save(update_fields=['inventory'])

# وقتی رزرو اتاق حذف شد
@receiver(post_delete, sender=ReservationRoom)
def update_room_inventory_on_delete(sender, instance, **kwargs):
    room = instance.room
    total_reserved = room.reservation_rooms.aggregate(total=Sum('quantity'))['total'] or 0
    room.inventory = max((room.initial_inventory or 0) - total_reserved, 0)
    room.save(update_fields=['inventory'])
