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
            old_balance = 0
        else:
            old_wallet = Wallet.objects.filter(pk=instance.pk).first()
            old_balance = old_wallet.balance if old_wallet else 0

        if instance.balance != old_balance:
            amount_increased = instance.balance - old_balance
            print(f"Wallet balance changed for user {instance.user.phone_number}. Old: {old_balance}, New: {instance.balance}, Difference: {amount_increased}")
            success = send_wallet_increase_sms(instance.user, amount_increased)
            if not success:
                print(f"Failed to send SMS for user {instance.user.phone_number} with amount {amount_increased}")
        else:
            print(f"No balance change for user {instance.user.phone_number}. Balance: {instance.balance}")
    except Exception as e:
        print(f"Error in wallet_balance_changed signal for user {instance.user.phone_number}: {str(e)}")
        logger.error(f"Error in signal: {str(e)}", exc_info=True)