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
    """ارسال SMS با تاخیر 120 ثانیه"""
    send_customer_club_deduct_sms(
        phone_number=phone_number,
        user_name=user_name,
        deducted_points=deducted_points,
        current_points=current_points
    )

_thread_locals = local()

def set_skip_points_and_sms(value):
    """تنظیم وضعیت رد کردن ارسال SMS در thread local"""
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    """دریافت وضعیت رد کردن ارسال SMS از thread local"""
    return getattr(_thread_locals, 'skip_points_and_sms', False)

@receiver(pre_save, sender=CustomerClubPoint)
def store_previous_points(sender, instance, **kwargs):
    """ذخیره مقدار قبلی امتیاز قبل از ذخیره‌سازی"""
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
    """ارسال SMS هنگام کاهش امتیاز کاربر"""
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
    """ارسال SMS هنگام ایجاد یا تغییر کد تخفیف"""
    if created or instance.users.exists():
        logger.info(f"ارسال SMS تخفیف برای کد {instance.code} به کاربران.")
        send_discount_sms(instance, send_to_all=True)

@receiver(pre_save, sender=DiscountActivationRecord)
def handle_manual_reward_claimed(sender, instance, **kwargs):
    """مدیریت تغییر وضعیت reward_claimed و کسر امتیاز"""
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
    """مدیریت تغییرات در activated_users برای همه انواع کدهای تخفیف"""
    logger.info(f"تغییر در activated_users کد تخفیف {instance.code}: action={action}, users={pk_set}")
    
    if action == 'post_add':
        for user_id in pk_set:
            try:
                user = BaseUser.objects.get(pk=user_id)
                
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

# سیگنال اصلی برای پردازش کد تخفیف رزرو هتل
@receiver(post_save, sender='reservation.Reservationhotel')
def handle_reservation_payment_for_discount(sender, instance, **kwargs):
    """پردازش کد تخفیف پس از پرداخت موفق رزرو"""
    from reservation.models import Reservationhotel
    
    # بررسی شرایط لازم برای پردازش کد تخفیف
    if (instance.payment_status == 'paid' and 
        instance.applied_discount_code and 
        not instance.discount_processed):
        
        logger.info(f"🟡 شروع پردازش کد تخفیف برای رزرو پرداخت شده {instance.tracking_code}")
        
        try:
            with transaction.atomic():
                # قفل کردن رکورد رزرو برای جلوگیری از پردازش تکراری
                reservation = Reservationhotel.objects.select_for_update().get(pk=instance.pk)
                if reservation.discount_processed:
                    logger.info(f"🔵 کد تخفیف برای رزرو {reservation.tracking_code} قبلاً پردازش شده است.")
                    return
                
                # پیدا کردن کد تخفیف
                discount_obj = None
                discount_type = None
                
                try:
                    discount_obj = RoomDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                    discount_type = 'room'
                    logger.info(f"🔵 کد تخفیف اتاق یافت شد: {discount_obj.code}")
                except RoomDiscountCode.DoesNotExist:
                    try:
                        discount_obj = HotelDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                        discount_type = 'hotel'
                        logger.info(f"🔵 کد تخفیف هتل یافت شد: {discount_obj.code}")
                    except HotelDiscountCode.DoesNotExist:
                        try:
                            discount_obj = ShoppingCenterDiscountCode.objects.select_for_update().get(code__iexact=reservation.applied_discount_code)
                            discount_type = 'shopping_center'
                            logger.info(f"🔵 کد تخفیف مرکز خرید یافت شد: {discount_obj.code}")
                        except ShoppingCenterDiscountCode.DoesNotExist:
                            logger.error(f"🔴 کد تخفیف {reservation.applied_discount_code} برای رزرو {reservation.tracking_code} یافت نشد")
                            return
                
                # 🔄 بررسی دفعات باقی‌مانده کد تخفیف
                if discount_obj.remaining_uses <= 0:
                    logger.warning(f"🔴 کد تخفیف {discount_obj.code} دفعات استفاده‌اش به پایان رسیده است (remaining_uses: {discount_obj.remaining_uses})")
                    # می‌توانید خطا ایجاد کنید یا اطلاع دهید
                    return
                
                # 🔄 بررسی اینکه کاربر قبلاً از این کد استفاده نکرده باشد
                if reservation.buyer in discount_obj.activated_users.all():
                    logger.warning(f"🔴 کاربر {reservation.buyer.phone_number} قبلاً از کد تخفیف {discount_obj.code} استفاده کرده است")
                    return
                
                logger.info(f"🟡 وضعیت کد تخفیف قبل از مصرف: remaining_uses={discount_obj.remaining_uses}, activated_users_count={discount_obj.activated_users.count()}")
                
                # 🔄 استفاده از متد consume_discount_for_user برای مصرف کد تخفیف
                try:
                    success = discount_obj.consume_discount_for_user(reservation.buyer)
                    
                    if success:
                        logger.info(f"🟢 کد تخفیف {discount_obj.code} با موفقیت مصرف شد - remaining_uses جدید: {discount_obj.remaining_uses}")
                        
                        # ایجاد رکورد فعال‌سازی
                        activation_record = _create_or_update_activation_record(reservation.buyer, discount_obj)
                        if activation_record:
                            logger.info(f"🟢 رکورد فعال‌سازی برای کاربر {reservation.buyer.phone_number} ایجاد شد")
                        
                        # علامت‌گذاری رزرو به عنوان پردازش شده
                        reservation.discount_processed = True
                        reservation.save(update_fields=['discount_processed'])
                        logger.info(f"🟢 کد تخفیف {discount_obj.code} برای رزرو {reservation.tracking_code} با موفقیت پردازش شد")
                    else:
                        logger.error(f"🔴 مصرف کد تخفیف {discount_obj.code} ناموفق بود")
                        
                except ValueError as e:
                    logger.error(f"🔴 خطا در مصرف کد تخفیف: {str(e)}")
                    return
                except Exception as e:
                    logger.error(f"🔴 خطای غیرمنتظره در مصرف کد تخفیف: {str(e)}")
                    return
                
        except Reservationhotel.DoesNotExist:
            logger.error(f"🔴 رزرو با ID {instance.pk} یافت نشد")
        except Exception as e:
            logger.error(f"🔴 خطا در پردازش کد تخفیف برای رزرو {instance.tracking_code}: {str(e)}")

# سیگنال برای مدیریت تغییرات remaining_uses
@receiver(pre_save, sender=RoomDiscountCode)
@receiver(pre_save, sender=HotelDiscountCode)
@receiver(pre_save, sender=ShoppingCenterDiscountCode)
def handle_discount_code_save(sender, instance, **kwargs):
    """مدیریت مقادیر پیش‌فرض هنگام ذخیره کد تخفیف"""
    if not instance.pk:
        # برای کدهای تخفیف جدید، remaining_uses را برابر usage_limit قرار بده
        if hasattr(instance, 'usage_limit') and hasattr(instance, 'remaining_uses'):
            if instance.remaining_uses == 0:  # فقط اگر مقدار پیش‌فرض باشد
                instance.remaining_uses = instance.usage_limit
                logger.info(f"🟡 تنظیم remaining_uses برای کد جدید {instance.code}: {instance.remaining_uses}")

# سیگنال برای لاگ کردن تغییرات remaining_uses
@receiver(post_save, sender=RoomDiscountCode)
@receiver(post_save, sender=HotelDiscountCode)
@receiver(post_save, sender=ShoppingCenterDiscountCode)
def log_discount_code_changes(sender, instance, created, **kwargs):
    """لاگ کردن تغییرات در کدهای تخفیف"""
    if created:
        logger.info(f"🟢 کد تخفیف جدید ایجاد شد: {instance.code} - remaining_uses: {instance.remaining_uses}")
    else:
        logger.info(f"🔵 کد تخفیف به روز شد: {instance.code} - remaining_uses: {instance.remaining_uses}")