import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F
from pydantic import ValidationError

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





# تنظیم لاگینگ برای دیباگ
logger = logging.getLogger(__name__)

@receiver(post_save, sender='your_app.ReservationRoomPassenger')
def add_to_passenger_book(sender, instance, created, **kwargs):
    """
    وقتی یک مسافر جدید در ReservationRoomPassenger ذخیره می‌شود،
    او را به دفترچه مسافران کاربر (Passenger) اضافه می‌کنیم.
    - مسافر اصلی باید تمام فیلدها (national_code و mobile_number) را داشته باشد.
    - سایر مسافران حتی بدون national_code یا mobile_number ثبت می‌شوند.
    
    Args:
        sender: مدل ReservationRoomPassenger
        instance: نمونه ذخیره‌شده از ReservationRoomPassenger
        created: آیا این یک رکورد جدید است؟
        **kwargs: آرگومان‌های اضافی
    """
    if not created:
        logger.debug(f"Skipping update for ReservationRoomPassenger {instance.id} (not created)")
        return

    # دسترسی به کاربر (buyer) از طریق زنجیره روابط
    try:
        user = instance.reservation_room.reservation.buyer
        if not user:
            logger.error(f"No buyer found for reservation {instance.reservation_room.reservation.id}")
            return
    except AttributeError as e:
        logger.error(f"Error accessing user for ReservationRoomPassenger {instance.id}: {e}")
        return

    # آماده‌سازی داده‌ها برای مدل Passenger
    phone_number = instance.mobile_number
    identification_code = instance.national_code

    # برای مسافر اصلی، بررسی اجباری بودن فیلدها
    if instance.passenger_type == 'primary':
        if not identification_code:
            logger.error(f"Primary passenger {instance.id} missing national_code")
            return
        if not phone_number or not re.match(r'^09\d{9}$', phone_number):
            logger.error(f"Primary passenger {instance.id} missing or invalid mobile_number: {phone_number}")
            return
    else:
        # برای سایر مسافران، اگر شماره موبایل یا کد شناسایی خالی باشد، مقدار پیش‌فرض
        if not phone_number or not re.match(r'^09\d{9}$', phone_number):
            phone_number = '09123456789'  # مقدار پیش‌فرض موقت
            logger.warning(f"Invalid or missing phone_number for ReservationRoomPassenger {instance.id}. Using default: {phone_number}")
        if not identification_code:
            identification_code = f"{instance.first_name}_{instance.last_name}_temp".replace(" ", "_")[:10]
            logger.warning(f"Missing national_code for ReservationRoomPassenger {instance.id}. Using temp ID: {identification_code}")

    # بررسی وجود مسافر در مدل Passenger
    try:
        passenger_exists = Passenger.objects.filter(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            identification_code=identification_code
        ).exists()

        if passenger_exists:
            logger.debug(f"Passenger with identification_code {identification_code} already exists for user {user.id}")
            return

        # ایجاد نمونه جدید در مدل Passenger
        passenger = Passenger.objects.create(
            user=user,
            first_name=instance.first_name,
            last_name=instance.last_name,
            phone_number=phone_number,
            identification_code=identification_code
        )
        logger.info(f"Passenger created for user {user.id} with identification_code {identification_code} (Passenger ID: {passenger.id})")
    except ValidationError as e:
        logger.error(f"Validation error creating Passenger for {instance.first_name} {instance.last_name}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating Passenger for {instance.first_name} {instance.last_name}: {e}")