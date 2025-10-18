import logging
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from threading import Timer, local
from django.db import transaction
from pydantic import ValidationError
from authentication.models import BaseUser
from .models import CustomerClubPoint, HotelDiscountCode, RoomDiscountCode, ShoppingCenterDiscountCode, DiscountActivationRecord
from .sms.sms import send_customer_club_deduct_sms, send_discount_sms

logger = logging.getLogger(__name__)

def delayed_send_deduct_sms(phone_number, user_name, deducted_points, current_points):
    send_customer_club_deduct_sms(
        phone_number=phone_number,
        user_name=user_name,
        deducted_points=deducted_points,
        current_points=current_points
    )

_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)

@receiver(pre_save, sender=CustomerClubPoint)
def store_previous_points(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = CustomerClubPoint.objects.get(pk=instance.pk)
            instance._previous_points = old.points
        except CustomerClubPoint.DoesNotExist:
            instance._previous_points = 0
    else:
        instance._previous_points = 0

@receiver(post_save, sender=CustomerClubPoint)
def send_club_points_sms(sender, instance, created, **kwargs):
    if get_skip_points_and_sms():
        logger.info(f"ارسال SMS برای کاربر {instance.user.phone_number} نادیده گرفته شد.")
        return

    added_points = instance.points - getattr(instance, '_previous_points', 0)
    if added_points < 0:
        logger.info(f"کاهش امتیاز برای کاربر {instance.user.phone_number}: {abs(added_points)} (امتیاز فعلی: {instance.points})")
        user_name = instance.user.first_name or instance.user.phone_number
        send_customer_club_deduct_sms(
            phone_number=instance.user.phone_number,
            user_name=user_name,
            deducted_points=abs(added_points),
            current_points=instance.points
        )
    else:
        logger.info(f"هیچ SMS برای افزایش امتیاز کاربر {instance.user.phone_number} ارسال نشد.")

@receiver(post_save, sender=RoomDiscountCode)
@receiver(post_save, sender=ShoppingCenterDiscountCode)
@receiver(post_save, sender=HotelDiscountCode)
def send_discount_sms_on_discount_code_save(sender, instance, created, **kwargs):
    if created or instance.users.exists():
        logger.info(f"ارسال SMS تخفیف برای کد {instance.code} به کاربران.")
        send_discount_sms(instance, send_to_all=True)

@receiver(pre_save, sender=DiscountActivationRecord)
def handle_manual_reward_claimed(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = DiscountActivationRecord.objects.get(pk=instance.pk)
            if not old_instance.reward_claimed and instance.reward_claimed:
                logger.info(f"reward_claimed برای رکورد {instance.id} به True تغییر کرد. بررسی کسر امتیاز...")
                discount_obj = instance.room_discount_code or instance.shopping_discount_code or instance.hotel_discount_code
                if not discount_obj:
                    logger.error(f"هیچ کد تخفیفی برای رکورد {instance.id} یافت نشد.")
                    return

                if discount_obj.required_points > 0:
                    with transaction.atomic():
                        customer_points, _ = CustomerClubPoint.objects.get_or_create(
                            user=instance.user,
                            defaults={'points': 0}
                        )
                        if instance.user in discount_obj.activated_users.all():
                            logger.info(f"امتیاز قبلاً برای کاربر {instance.user.phone_number} کسر شده است (کاربر در activated_users). کسر مجدد نادیده گرفته شد.")
                            return
                        if customer_points.points < discount_obj.required_points:
                            logger.error(f"امتیاز کافی برای کسر {discount_obj.required_points} از کاربر {instance.user.phone_number} وجود ندارد.")
                            raise ValidationError("امتیاز کافی برای استفاده از کد تخفیف نیست.")
                        customer_points.points -= discount_obj.required_points
                        set_skip_points_and_sms(True)
                        customer_points.save()
                        set_skip_points_and_sms(False)
                        logger.info(f"امتیاز {discount_obj.required_points} از کاربر {instance.user.phone_number} برای کد تخفیف {discount_obj.code} کسر شد.")
                        Timer(120, delayed_send_deduct_sms, args=(
                            instance.user.phone_number,
                            instance.user.first_name or instance.user.phone_number,
                            discount_obj.required_points,
                            customer_points.points
                        )).start()
        except DiscountActivationRecord.DoesNotExist:
            logger.error(f"رکورد DiscountActivationRecord با ID {instance.id} یافت نشد.")

@receiver(m2m_changed, sender=RoomDiscountCode.activated_users.through)
@receiver(m2m_changed, sender=HotelDiscountCode.activated_users.through)
@receiver(m2m_changed, sender=ShoppingCenterDiscountCode.activated_users.through)
def handle_manual_activated_users(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        logger.info(f"کاربر(ان) {pk_set} به activated_users کد تخفیف {instance.code} اضافه شدند.")
        for user_id in pk_set:
            try:
                user = BaseUser.objects.get(pk=user_id)
                discount_type = 'room' if isinstance(instance, RoomDiscountCode) else 'hotel' if isinstance(instance, HotelDiscountCode) else 'shopping_center'
                activation_filter = {
                    'user': user,
                    'discount_type': discount_type,
                    **({'room_discount_code': instance} if isinstance(instance, RoomDiscountCode) else {'hotel_discount_code': instance} if isinstance(instance, HotelDiscountCode) else {'shopping_discount_code': instance}),
                }
                activation_record = DiscountActivationRecord.objects.filter(**activation_filter).first()
                if not activation_record:
                    logger.info(f"ایجاد رکورد فعال‌سازی برای کاربر {user.phone_number} و کد تخفیف {instance.code}")
                    kwargs = {
                        "user": user,
                        "discount_type": discount_type,
                        "reward_claimed": True
                    }
                    if discount_type == "room":
                        kwargs["room_discount_code"] = instance
                    elif discount_type == "hotel":
                        kwargs["hotel_discount_code"] = instance
                    else:
                        kwargs["shopping_discount_code"] = instance
                    DiscountActivationRecord.objects.create(**kwargs)
                elif not activation_record.reward_claimed:
                    logger.info(f"به‌روزرسانی رکورد فعال‌سازی برای کاربر {user.phone_number}: reward_claimed=True")
                    activation_record.reward_claimed = True
                    activation_record.save(update_fields=['reward_claimed'])

                if instance.required_points > 0:
                    with transaction.atomic():
                        customer_points, _ = CustomerClubPoint.objects.get_or_create(
                            user=user,
                            defaults={'points': 0}
                        )
                        if customer_points.points < instance.required_points:
                            logger.error(f"امتیاز کافی برای کسر {instance.required_points} از کاربر {user.phone_number} وجود ندارد.")
                            raise ValidationError("امتیاز کافی برای استفاده از کد تخفیف نیست.")
                        customer_points.points -= instance.required_points
                        set_skip_points_and_sms(True)
                        customer_points.save()
                        set_skip_points_and_sms(False)
                        logger.info(f"امتیاز {instance.required_points} از کاربر {user.phone_number} برای کد تخفیف {instance.code} کسر شد.")
                        Timer(120, delayed_send_deduct_sms, args=(
                            user.phone_number,
                            user.first_name or user.phone_number,
                            instance.required_points,
                            customer_points.points
                        )).start()
            except BaseUser.DoesNotExist:
                logger.error(f"کاربر با ID {user_id} یافت نشد.")
            except ValidationError as e:
                logger.error(f"خطای اعتبارسنجی برای کاربر {user_id}: {str(e)}")
            except Exception as e:
                logger.error(f"خطای غیرمنتظره برای کاربر {user_id}: {str(e)}")