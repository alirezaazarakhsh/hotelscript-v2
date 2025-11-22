from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Wallet, DepositReceipt
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


@receiver(pre_save, sender=DepositReceipt)
def deposit_receipt_approved(sender, instance, **kwargs):
    """
    سیگنال برای افزایش موجودی کیف پول کاربر پس از تایید فیش واریز توسط ادمین.
    """
    if instance.pk:
        try:
            old_instance = DepositReceipt.objects.get(pk=instance.pk)
            # بررسی: اگر قبلاً تایید نشده بود و حالا تایید شد
            if not old_instance.is_approved and instance.is_approved and instance.user:
                wallet, created = Wallet.objects.get_or_create(user=instance.user, defaults={'balance': 0})
                wallet.balance += int(instance.amount)
                wallet.save()
                logger.info(f"Deposit approved: Added {instance.amount} to wallet of user {instance.user.phone_number}")
                print(f"✓ فیش واریز تایید شد. مبلغ {instance.amount:,.0f} تومان به کیف پول کاربر {instance.user.phone_number} اضافه شد.")
        except DepositReceipt.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error in deposit_receipt_approved signal: {str(e)}", exc_info=True)