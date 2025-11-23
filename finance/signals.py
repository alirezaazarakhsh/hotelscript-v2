from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Wallet, DepositReceipt, WithdrawalRequest


@receiver(post_save, sender=WithdrawalRequest)
def withdrawal_request_status_changed(sender, instance, created, **kwargs):
    """
    سیگنال برای کسر موجودی از کیف پول کاربر پس از تایید درخواست برداشت توسط ادمین.
    """
    if not created and instance.status == 'approved' and not instance.wallet_debited and instance.user:
        try:
            # دریافت کیف پول کاربر
            wallet = Wallet.objects.get(user=instance.user)
            
            # تبدیل مبلغ به عدد صحیح (تومان)
            amount_to_deduct = int(instance.amount)
            
            # بررسی موجودی کافی
            if wallet.balance >= amount_to_deduct:
                wallet.balance -= amount_to_deduct
                wallet.save()
                
                # علامت‌گذاری که مبلغ از کیف پول کسر شده
                WithdrawalRequest.objects.filter(pk=instance.pk).update(wallet_debited=True)
                
                logger.info(f"Withdrawal approved: Deducted {amount_to_deduct:,} from wallet of user {instance.user.phone_number}")
                print(f"✓ درخواست برداشت تایید شد. مبلغ {amount_to_deduct:,} تومان از کیف پول کاربر {instance.user.phone_number} کسر شد.")
            else:
                logger.error(f"Insufficient balance for withdrawal request {instance.pk}. Required: {amount_to_deduct:,}, Available: {wallet.balance:,}")
                print(f"✗ موجودی کافی نیست. مبلغ درخواستی: {amount_to_deduct:,}، موجودی فعلی: {wallet.balance:,}")
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for user {instance.user.phone_number} in withdrawal request {instance.pk}")
            print(f"✗ کیف پول برای کاربر {instance.user.phone_number} یافت نشد.")
        except Exception as e:
            logger.error(f"Error in withdrawal_request_status_changed signal: {str(e)}", exc_info=True)
            print(f"✗ خطا در پردازش درخواست برداشت: {str(e)}")
from finance.sms.sms import send_wallet_increase_sms
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


@receiver(post_save, sender=DepositReceipt)
def deposit_receipt_approved(sender, instance, created, **kwargs):
    """
    سیگنال برای افزایش موجودی کیف پول کاربر پس از تایید فیش واریز توسط ادمین.
    """
    if not created and instance.is_approved and not instance.wallet_credited and instance.user:
        try:
            # دریافت یا ایجاد کیف پول کاربر
            wallet, wallet_created = Wallet.objects.get_or_create(
                user=instance.user,
                defaults={'balance': 0}
            )
            # تبدیل مبلغ به عدد صحیح (تومان)
            amount_to_add = int(instance.amount)
            wallet.balance += amount_to_add
            wallet.save()
            
            # علامت‌گذاری که مبلغ به کیف پول اضافه شده
            DepositReceipt.objects.filter(pk=instance.pk).update(wallet_credited=True)
            
            logger.info(f"Deposit approved: Added {amount_to_add:,} to wallet of user {instance.user.phone_number}")
            print(f"✓ فیش واریز تایید شد. مبلغ {amount_to_add:,} تومان به کیف پول کاربر {instance.user.phone_number} اضافه شد.")
        except Exception as e:
            logger.error(f"Error in deposit_receipt_approved signal: {str(e)}", exc_info=True)