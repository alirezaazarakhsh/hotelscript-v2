import logging
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


from authentication.models import (
    BaseUser,
    NaturalProfile,
)
from finance.sms.sms import send_wallet_increase_sms


#مبلغ انتخابی برای کیف پول 
class WalletPack(models.Model):
    id = models.AutoField(primary_key=True)
    amount_1 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='مبلغ پکیج یک', help_text='مبلغ پیش‌فرض برای پکیج اول')
    amount_2 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='مبلغ پکیج دوم', help_text='مبلغ پیش‌فرض برای پکیج دوم')
    amount_3 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='مبلغ پکیج سوم', help_text='مبلغ پیش‌فرض برای پکیج سوم')
    amount_4 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='مبلغ پکیج چهارم', help_text='مبلغ پیش‌فرض برای پکیج چهارم')

    class Meta:
        verbose_name = 'اضافه کردن سقف کیف پول'
        verbose_name_plural = 'تنظیم سقف شارژ کیف پول'

    def __str__(self):
        return f'پکیج {self.id} با مبالغ: {self.amount_1:,.0f}, {self.amount_2:,.0f}, {self.amount_3:,.0f}, {self.amount_4:,.0f} تومان'




# مدل کیف پول کاربر برای موجودی 
logger = logging.getLogger(__name__)

class Wallet(models.Model):
    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='wallet',
    )
    balance = models.PositiveBigIntegerField(
        verbose_name=_('موجودی'),
    )

    class Meta:
        verbose_name = 'کیف پول'
        verbose_name_plural = 'کیف پول‌ها'

    def __str__(self):
        try:
            natural_profile = self.user.natural_profile
            return f'{natural_profile.first_name or ""} {natural_profile.last_name or ""}'.strip()
        except NaturalProfile.DoesNotExist:
            return f'{self.user.phone_number} (بدون پروفایل)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def deduct(self, amount, reservation=None):
        """
        کسر از کیف پول با مدیریت تراکنش
        """
        if amount <= 0:
            raise ValueError("مبلغ باید بزرگتر از صفر باشد")
            
        if self.balance < amount:
            raise ValueError("موجودی کافی نیست")
            
        with transaction.atomic():
            # استفاده از F() expression برای جلوگیری از race condition
            Wallet.objects.filter(pk=self.pk).update(
                balance=models.F('balance') - amount
            )
            
            # رفرش کردن آبجکت برای گرفتن مقدار جدید
            self.refresh_from_db()
            
            logger.info(f"✅ مبلغ {amount} از کیف پول کاربر {self.user.phone_number} کسر شد. موجودی جدید: {self.balance}")
            
            # ایجاد تراکنش برای تاریخچه (اختیاری)
            if reservation:
                from .models import WalletTransaction  # اگر مدل تراکنش دارید
                WalletTransaction.objects.create(
                    wallet=self,
                    amount=amount,
                    transaction_type='withdrawal',
                    description=f'برداشت برای رزرو {reservation.tracking_code}',
                    related_reservation=reservation
                )
            
        return True