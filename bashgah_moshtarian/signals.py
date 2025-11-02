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

def _get_discount_type(instance):
    """تعیین نوع کد تخفیف"""
    if isinstance(instance, RoomDiscountCode):
        return 'room'
    elif isinstance(instance, HotelDiscountCode):
        return 'hotel'
    elif isinstance(instance, ShoppingCenterDiscountCode):
        return 'shopping_center'
    return None

def _create_or_update_activation_record(user, discount_instance):
    """ایجاد یا به روزرسانی رکورد فعال‌سازی"""
    discount_type = _get_discount_type(discount_instance)
    if not discount_type:
        logger.error(f"نوع کد تخفیف نامعتبر: {type(discount_instance)}")
        return None
    
    activation_filter = {
        'user': user,
        'discount_type': discount_type,
    }
    
    # تنظیم فیلد مناسب بر اساس نوع کد تخفیف
    if discount_type == 'room':
        activation_filter['room_discount_code'] = discount_instance
    elif discount_type == 'hotel':
        activation_filter['hotel_discount_code'] = discount_instance
    elif discount_type == 'shopping_center':
        activation_filter['shopping_discount_code'] = discount_instance
    
    try:
        activation_record, created = DiscountActivationRecord.objects.get_or_create(
            **activation_filter,
            defaults={'reward_claimed': True}
        )
        
        if not created and not activation_record.reward_claimed:
            activation_record.reward_claimed = True
            activation_record.save(update_fields=['reward_claimed'])
        
        logger.info(f"{'ایجاد' if created else 'به روزرسانی'} رکورد فعال‌سازی برای کاربر {user.phone_number} و کد {discount_instance.code}")
        return activation_record
        
    except Exception as e:
        logger.error(f"خطا در ایجاد/به روزرسانی رکورد فعال‌سازی: {str(e)}")
        return None

def _deduct_points_for_activation(user, discount_instance):
    """کسر امتیاز برای فعال‌سازی کد تخفیف"""
    if discount_instance.required_points <= 0:
        return True
        
    try:
        with transaction.atomic():
            customer_points, _ = CustomerClubPoint.objects.get_or_create(
                user=user,
                defaults={'points': 0}
            )
            
            if user in discount_instance.activated_users.all():
                logger.info(f"امتیاز قبلاً برای کاربر {user.phone_number} کسر شده است. کسر مجدد نادیده گرفته شد.")
                return True
                
            if customer_points.points < discount_instance.required_points:
                logger.error(f"امتیاز کافی برای کسر {discount_instance.required_points} از کاربر {user.phone_number} وجود ندارد.")
                return False
                
            customer_points.points -= discount_instance.required_points
            set_skip_points_and_sms(True)
            customer_points.save()
            set_skip_points_and_sms(False)
            
            logger.info(f"امتیاز {discount_instance.required_points} از کاربر {user.phone_number} برای کد تخفیف {discount_instance.code} کسر شد.")
            
            # ارسال SMS با تاخیر
            Timer(120, delayed_send_deduct_sms, args=(
                user.phone_number,
                user.first_name or user.phone_number,
                discount_instance.required_points,
                customer_points.points
            )).start()
            
            return True
            
    except Exception as e:
        logger.error(f"خطا در کسر امتیاز برای کاربر {user.phone_number}: {str(e)}")
        return False

@receiver(m2m_changed, sender=RoomDiscountCode.activated_users.through)
@receiver(m2m_changed, sender=HotelDiscountCode.activated_users.through)
@receiver(m2m_changed, sender=ShoppingCenterDiscountCode.activated_users.through)
def handle_activated_users_change(sender, instance, action, pk_set, **kwargs):
    """مدیریت تغییرات در activated_users برای همه انواع کدهای تخفیف - نسخه اصلاح شده"""
    logger.info(f"تغییر در activated_users کد تخفیف {instance.code}: action={action}, users={pk_set}")
    
    if action == 'post_add':
        for user_id in pk_set:
            try:
                user = BaseUser.objects.get(pk=user_id)
                
                # کاهش remaining_uses برای کدهای اتاق و هتل
                if hasattr(instance, 'remaining_uses') and isinstance(instance, (RoomDiscountCode, HotelDiscountCode)):
                    try:
                        with transaction.atomic():
                            # استفاده از select_for_update برای جلوگیری از race condition
                            discount_obj = type(instance).objects.select_for_update().get(pk=instance.pk)
                            
                            if discount_obj.remaining_uses <= 0:
                                logger.error(f"❌ تعداد دفعات استفاده از کد {discount_obj.code} به پایان رسیده است.")
                                # حذف کاربر از activated_users
                                discount_obj.activated_users.remove(user)
                                continue
                            
                            logger.info(f"🟡 کاهش remaining_uses برای کد {discount_obj.code} - قبل: {discount_obj.remaining_uses}")
                            
                            # کاهش دفعات باقی‌مانده با استفاده از F expression
                            type(instance).objects.filter(pk=discount_obj.pk).update(
                                remaining_uses=models.F('remaining_uses') - 1
                            )
                            
                            # رفرش برای گرفتن مقدار جدید
                            discount_obj.refresh_from_db()
                            
                            logger.info(f"🟢 remaining_uses برای کد {discount_obj.code} کاهش یافت - بعد: {discount_obj.remaining_uses} - کاربر: {user.phone_number}")
                            
                    except Exception as e:
                        logger.error(f"❌ خطا در کاهش remaining_uses برای کد {instance.code}: {str(e)}")
                        # حذف کاربر از activated_users در صورت شکست
                        instance.activated_users.remove(user)
                        continue
                
                # ایجاد یا به روزرسانی رکورد فعال‌سازی
                activation_record = _create_or_update_activation_record(user, instance)
                if not activation_record:
                    logger.error(f"خطا در ایجاد رکورد فعال‌سازی برای کاربر {user_id}")
                    continue
                
                # کسر امتیاز در صورت نیاز
                if not _deduct_points_for_activation(user, instance):
                    logger.error(f"خطا در کسر امتیاز برای کاربر {user.phone_number}")
                    # حذف کاربر از activated_users در صورت شکست
                    instance.activated_users.remove(user)
                    
            except BaseUser.DoesNotExist:
                logger.error(f"کاربر با ID {user_id} یافت نشد.")
            except Exception as e:
                logger.error(f"خطای غیرمنتظره برای کاربر {user_id}: {str(e)}")

# سیگنال جدید برای رزروهای پرداخت شده
@receiver(post_save, sender='reservation.Reservationhotel')
def handle_reservation_payment_for_discount(sender, instance, **kwargs):
    """پردازش کد تخفیف پس از پرداخت موفق رزرو - نسخه اصلاح شده"""
    from reservation.models import Reservationhotel
    
    if (instance.payment_status == 'paid' and 
        instance.applied_discount_code and 
        not instance.discount_processed):
        
        logger.info(f"🔵 پردازش کد تخفیف برای رزرو پرداخت شده {instance.tracking_code}")
        
        try:
            with transaction.atomic():
                reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                if reservation.discount_processed:
                    return
                
                # پیدا کردن کد تخفیف
                discount_obj = None
                discount_type = None
                
                try:
                    discount_obj = RoomDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                    discount_type = 'room'
                except RoomDiscountCode.DoesNotExist:
                    try:
                        discount_obj = HotelDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                        discount_type = 'hotel'
                    except HotelDiscountCode.DoesNotExist:
                        logger.error(f"کد تخفیف {reservation.applied_discount_code} برای رزرو {reservation.tracking_code} یافت نشد")
                        return
                
                # افزودن کاربر به activated_users - این باعث فعال شدن سیگنال بالا می‌شود
                if reservation.buyer not in discount_obj.activated_users.all():
                    discount_obj.activated_users.add(reservation.buyer)
                    logger.info(f"کاربر {reservation.buyer.phone_number} به activated_users کد {discount_obj.code} اضافه شد")
                
                # علامت‌گذاری رزرو به عنوان پردازش شده
                reservation.discount_processed = True
                reservation.save(update_fields=['discount_processed'])
                logger.info(f"کد تخفیف {discount_obj.code} برای رزرو {reservation.tracking_code} با موفقیت پردازش شد")
                
        except Exception as e:
            logger.error(f"خطا در پردازش کد تخفیف برای رزرو {instance.tracking_code}: {str(e)}")