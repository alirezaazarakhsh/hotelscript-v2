from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


from authentication.models import (
    BaseUser,
    NaturalProfile,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
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
        
        

#مدل شماره کارت ادمین 
class AdminCardSettings(models.Model):
    card_number = models.CharField(
        max_length=16,
        verbose_name=_("شماره کارت"),
        help_text=_("شماره کارت ۱۶ رقمی بدون فاصله"),
    )
    iban_number = models.CharField(
        max_length=24,
        verbose_name=_("شماره شبا"),
        help_text=_("شماره شبا ۲۴ رقمی"),
    )
    account_holder_name = models.CharField(
        max_length=255,
        verbose_name=_("نام صاحب حساب"),
        help_text=_("نام کامل صاحب حساب"),
    )

    class Meta:
        verbose_name = _("تنظیمات شماره کارت ادمین")
        verbose_name_plural = _("تنظیمات شماره کارت ادمین‌ها")

    def __str__(self):
        return f"{self.account_holder_name} - {self.card_number}"
    
    
    
#مدل فیش واریز دستی کاربران 
class DepositReceipt(models.Model):
    PROFILE_TYPE_CHOICES = (
        ('natural', 'حقیقی'),
        ('juridical', 'حقوقی'),
    )

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='deposit_receipts',
        null=True,
        blank=True,
    )
    profile_type = models.CharField(
        max_length=10,
        choices=PROFILE_TYPE_CHOICES,
        verbose_name=_('نوع پروفایل'),
        null=True,
        blank=True,
    )
    profile_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ["naturalprofile", "juridicalprofile"]},
        verbose_name=_('نوع پروفایل'),
        related_name='depositreceipt_profile_content_type',
        null=True,
        blank=True,
    )
    profile_object_id = models.PositiveIntegerField(verbose_name=_('شناسه پروفایل'), null=True, blank=True)
    profile = GenericForeignKey('profile_content_type', 'profile_object_id')

    card_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ["cardnumber", "juridicalcardnumber"]},
        verbose_name=_('نوع شماره کارت'),
        related_name='depositreceipt_card_content_type',
        null=True,
        blank=True,
    )
    card_object_id = models.PositiveIntegerField(verbose_name=_('شناسه شماره کارت'), null=True, blank=True)
    card = GenericForeignKey('card_content_type', 'card_object_id')

    depositor_name = models.CharField(
        max_length=255,
        verbose_name=_("نام واریز کننده"),
        null=True,
        blank=True,
        default=None,
    )
    tracking_number = models.CharField(
        max_length=12,
        unique=True,
        verbose_name=_("شماره پیگیری"),
        help_text=_("شماره پیگیری ۱۲ رقمی"),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("مبلغ واریز"),
        validators=[MinValueValidator(1)],
    )
    deposit_date_jalali = models.CharField(
        max_length=10,
        verbose_name=_("تاریخ واریز (شمسی)"),
        help_text=_("فرمت: YYYY/MM/DD"),
    )
    receipt_image = models.ImageField(
        upload_to='deposit_receipts/',
        verbose_name=_("عکس فیش"),
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_("تایید شده"),
        help_text=_("آیا این فیش واریز توسط ادمین تایید شده است؟"),
    )
    wallet_credited = models.BooleanField(
        default=False,
        verbose_name=_("اضافه شده به کیف پول"),
        help_text=_("آیا این مبلغ به کیف پول کاربر اضافه شده است؟"),
        editable=False,
    )
    # فیلدهای صریح برای شماره کارت و شبا جهت شفافیت و آرشیو مستقل از تغییرات بعدی کارت
    card_number = models.CharField(
        max_length=16,
        verbose_name=_('شماره کارت استفاده‌شده'),
        null=True,
        blank=True,
        help_text=_('شماره کارت دقیقا در لحظه ثبت فیش ذخیره می‌شود.'),
        validators=[RegexValidator(r'^\d{16}$', _('شماره کارت باید ۱۶ رقم باشد.'))]
    )
    card_iban = models.CharField(
        max_length=24,
        verbose_name=_('شبا استفاده‌شده'),
        null=True,
        blank=True,
        help_text=_('شبا مرتبط با کارت در لحظه ثبت فیش (اختیاری).'),
        validators=[RegexValidator(r'^\d{24}$', _('شماره شبا باید ۲۴ رقم باشد.'))]
    )

    class Meta:
        verbose_name = _("فیش واریزی")
        verbose_name_plural = _("فیش‌های واریزی کاربران")

    def __str__(self):
        return f"{self.depositor_name or 'واریز'} - {self.amount} تومان - {self.tracking_number}"
    
    def get_card_info(self):
        """دریافت اطلاعات شماره کارت و شبا"""
        if self.card:
            return {
                'card_number': self.card.card_number,
                'iban': self.card.iban,
                'account_holder': self.card.account_holder_name,
            }
        return None

    def save(self, *args, **kwargs):
        # هنگام ذخیره (اولین بار) اگر کارت ست شده بود و snapshot خالی بود، آن را ذخیره کن
        if self.card and (not self.card_number):
            self.card_number = getattr(self.card, 'card_number', None)
            self.card_iban = getattr(self.card, 'iban', None)
        super().save(*args, **kwargs)
    
    def get_profile_info(self):
        """دریافت اطلاعات پروفایل (حقیقی یا حقوقی)"""
        if self.profile:
            if self.profile_type == 'natural':
                return {
                    'type': 'حقیقی',
                    'first_name': self.profile.first_name,
                    'last_name': self.profile.last_name,
                    'national_code': self.profile.national_code,
                }
            elif self.profile_type == 'juridical':
                return {
                    'type': 'حقوقی',
                    'organization_name': self.profile.organization_name,
                    'national_id': self.profile.national_id,
                }
        return None


#مدل درخواست برداشت از کیف پول
class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('completed', 'واریز شده'),
    )
    
    PROFILE_TYPE_CHOICES = (
        ('natural', 'حقیقی'),
        ('juridical', 'حقوقی'),
    )

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_('کاربر'),
        related_name='withdrawal_requests',
    )
    
    profile_type = models.CharField(
        max_length=10,
        choices=PROFILE_TYPE_CHOICES,
        verbose_name=_('نوع پروفایل'),
    )
    
    profile_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ["naturalprofile", "juridicalprofile"]},
        verbose_name=_('نوع پروفایل'),
        related_name='withdrawalrequest_profile_content_type',
    )
    profile_object_id = models.PositiveIntegerField(verbose_name=_('شناسه پروفایل'))
    profile = GenericForeignKey('profile_content_type', 'profile_object_id')

    card_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ["cardnumber", "juridicalcardnumber"]},
        verbose_name=_('نوع شماره کارت مقصد'),
        related_name='withdrawalrequest_card_content_type',
    )
    card_object_id = models.PositiveIntegerField(verbose_name=_('شناسه شماره کارت مقصد'))
    card = GenericForeignKey('card_content_type', 'card_object_id')

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("مبلغ برداشت"),
        validators=[MinValueValidator(1)],
        help_text=_("مبلغ درخواستی برای برداشت از کیف پول (تومان)"),
    )
    
    # فیلدهای ذخیره اطلاعات کارت در زمان درخواست
    card_number = models.CharField(
        max_length=16,
        verbose_name=_('شماره کارت مقصد'),
        help_text=_('شماره کارت در لحظه ثبت درخواست ذخیره می‌شود.'),
        validators=[RegexValidator(r'^\d{16}$', _('شماره کارت باید ۱۶ رقم باشد.'))]
    )
    card_iban = models.CharField(
        max_length=24,
        verbose_name=_('شبا کارت مقصد'),
        null=True,
        blank=True,
        help_text=_('شبا مرتبط با کارت در لحظه ثبت درخواست.'),
        validators=[RegexValidator(r'^\d{24}$', _('شماره شبا باید ۲۴ رقم باشد.'))]
    )
    card_holder_name = models.CharField(
        max_length=255,
        verbose_name=_("نام صاحب کارت مقصد"),
        help_text=_("نام صاحب حساب در لحظه ثبت درخواست"),
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("وضعیت درخواست"),
    )
    
    wallet_debited = models.BooleanField(
        default=False,
        verbose_name=_("کسر شده از کیف پول"),
        help_text=_("آیا این مبلغ از کیف پول کاربر کسر شده است؟"),
        editable=False,
    )
    
    admin_note = models.TextField(
        verbose_name=_("یادداشت ادمین"),
        blank=True,
        null=True,
        help_text=_("توضیحات ادمین درباره این درخواست (در صورت رد یا...)"),
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ثبت درخواست"),
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین بروزرسانی"),
    )

    class Meta:
        verbose_name = _("درخواست برداشت")
        verbose_name_plural = _("درخواست‌های برداشت از کیف پول")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} - {self.amount:,.0f} تومان - {self.get_status_display()}"
    
    def get_card_info(self):
        """دریافت اطلاعات شماره کارت مقصد"""
        if self.card:
            return {
                'card_number': self.card.card_number,
                'iban': getattr(self.card, 'iban', None),
                'account_holder': self.card.account_holder_name,
            }
        return None

    def get_profile_info(self):
        """دریافت اطلاعات پروفایل (حقیقی یا حقوقی)"""
        if self.profile:
            if self.profile_type == 'natural':
                return {
                    'type': 'حقیقی',
                    'first_name': self.profile.first_name,
                    'last_name': self.profile.last_name,
                    'national_code': self.profile.national_code,
                }
            elif self.profile_type == 'juridical':
                return {
                    'type': 'حقوقی',
                    'organization_name': self.profile.organization_name,
                    'national_id': self.profile.national_id,
                }
        return None

    def save(self, *args, **kwargs):
        # ذخیره اطلاعات کارت در زمان ایجاد درخواست
        if not self.pk and self.card:
            self.card_number = getattr(self.card, 'card_number', '')
            self.card_iban = getattr(self.card, 'iban', None)
            self.card_holder_name = getattr(self.card, 'account_holder_name', '')
        super().save(*args, **kwargs)


# لاگ افزایش موجودی از درگاه (همیشه موفق در صورت ثبت)
class WalletTopUpLog(models.Model):
    GATEWAY_CHOICES = (
        ('zarinpal', 'زرین‌پال'),
        ('iraniangateway', 'ایران‌درگاه'),
    )
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='wallet_topups', verbose_name=_('کاربر'))
    amount = models.PositiveBigIntegerField(verbose_name=_('مبلغ افزایش'), help_text=_('مبلغ افزایش یافته به تومان'))
    gateway = models.CharField(max_length=32, choices=GATEWAY_CHOICES, verbose_name=_('درگاه'))
    authority_or_order = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('شناسه تراکنش'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ثبت'))

    class Meta:
        verbose_name = _('لاگ افزایش موجودی')
        verbose_name_plural = _('لاگ‌های افزایش موجودی کیف پول')
        ordering = ['-created_at']

    def __str__(self):
        return f"TopUp {self.user.phone_number} +{self.amount:,} تومان via {self.gateway}"
