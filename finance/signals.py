from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet
from .sms import send_wallet_increase_sms
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Wallet)
def wallet_balance_changed(sender, instance, created, **kwargs):
    """
    سیگنال برای بررسی تغییر موجودی کیف پول و ارسال SMS در صورت افزایش.
    """
    try:
        if created:
            # اگر کیف پول جدید ایجاد شده، فرض می‌کنیم موجودی اولیه صفر بوده است
            old_balance = 0
        else:
            # گرفتن نسخه قبلی کیف پول از دیتابیس
            old_wallet = Wallet.objects.get(pk=instance.pk)
            old_balance = old_wallet.balance

        if instance.balance != old_balance:
            amount_increased = instance.balance - old_balance
            logger.debug(f"Wallet balance changed for user {instance.user}. Old: {old_balance}, New: {instance.balance}, Difference: {amount_increased}")
            send_wallet_increase_sms(instance.user, amount_increased)
    except Wallet.DoesNotExist:
        logger.error(f"Wallet with pk {instance.pk} does not exist for user {instance.user}.")
    except Exception as e:
        logger.error(f"Error in wallet_balance_changed signal: {str(e)}", exc_info=True)