from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F

from reservation.models import Passenger, ReservationRoom, ReservationRoomPassenger

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




from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ReservationRoomPassenger)
def add_to_passenger_book(sender, instance, created, **kwargs):
    """
    وقتی یک مسافر رزرو ذخیره شد، او را به دفترچه مسافران کاربر اضافه می‌کنیم.
    """
    if not created:
        return  # فقط برای رکوردهای جدید

    user = instance.reservation_room.reservation.buyer
    if not instance.national_code:
        return  # اگر کد ملی/پاسپورت موجود نبود، اضافه نمی‌کنیم

    # چک می‌کنیم که مسافر قبلاً وجود نداشته باشد
    passenger_exists = Passenger.objects.filter(
        user=user,
        identification_code=instance.national_code
    ).exists()

    if not passenger_exists:
        Passenger.objects.create(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            phone_number=instance.mobile_number or '',  # در صورت نبود موبایل خالی می‌گذاریم
            identification_code=instance.national_code
        )
