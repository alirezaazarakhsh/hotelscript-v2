from venv import logger
from django.db import models
from django.core.validators import RegexValidator
from django.db import transaction
from authentication.models import BaseUser
from config.models import UserLevel
from django_jalali.db import models as jmodels
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

# مدل کد تخفیف باشگاه مشتری برای اتاق‌ها
class RoomDiscountCode(models.Model):
    room = models.ForeignKey(
        'reservation.Room',
        on_delete=models.CASCADE,
        related_name='discount_codes',
        verbose_name=_("اتاق")
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[RegexValidator(r'^\d+$', message=_("فقط مقادیر عددی مجاز هستند."))],
        verbose_name=_("مقدار تخفیف"),
        help_text=_("مقدار تخفیف را به تومان وارد کنید (فقط عدد).")
    )
    users = models.ManyToManyField(
        BaseUser,
        related_name='targeted_discount_codes',
        verbose_name=_("کاربران"),
        blank=True,
        help_text=_("کاربرانی که این کد تخفیف برای آن‌ها هدف‌گذاری شده است.")
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        verbose_name=_("کد تخفیف"),
        help_text=_("کد تخفیف ۸ رقمی را وارد کنید.")
    )
    usage_limit = models.PositiveIntegerField(
        default=1,
        verbose_name=_("حداکثر دفعات استفاده"),
        help_text=_("تعداد کل دفعات مجاز استفاده از این کد تخفیف (ثابت)")
    )
    remaining_uses = models.PositiveIntegerField(
        default=0,
        verbose_name=_("دفعات باقی‌مانده"),
        help_text=_("تعداد دفعات باقی‌مانده برای استفاده از این کد تخفیف")
    )
    required_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز مورد نیاز"),
        help_text=_("حداقل امتیازی که کاربر باید داشته باشد تا بتواند از کد استفاده کند")
    )
    user_level = models.ForeignKey(
        UserLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='discount_codes',
        verbose_name=_("سطح کاربری"),
        help_text=_("سطوح کاربری که این کد تخفیف برای آن‌ها قابل استفاده است. اگر خالی باشد، برای همه سطوح اعمال می‌شود.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد")
    )
    expires_at = jmodels.jDateField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ انقضا (شمسی)")
    )
    activation_rules = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("قوانین فعال‌سازی"),
        help_text=_("می‌توانید قوانینی برای نحوه فعال‌سازی این کد وارد کنید.")
    )
    activated_users = models.ManyToManyField(
        BaseUser,
        related_name='activated_room_discount_codes',
        verbose_name=_("کاربران استفاده‌کننده"),
        blank=True,
        help_text=_("کاربرانی که از این کد تخفیف برای رزرو استفاده کرده‌اند.")
    )

    def __str__(self):
        return f"{self.code} - {self.discount_value}"

    def get_users_with_names(self):
        result = []
        for user in self.users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def get_activated_users_with_names(self):
        result = []
        for user in self.activated_users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def consume_discount_for_user(self, user):
        """
        متد یکپارچه برای مصرف کد تخفیف - کاهش remaining_uses و افزودن کاربر
        """
        try:
            with transaction.atomic():
                # استفاده از select_for_update برای جلوگیری از race condition
                discount_obj = RoomDiscountCode.objects.select_for_update().get(pk=self.pk)
                
                if discount_obj.remaining_uses <= 0:
                    raise ValueError(f"تعداد دفعات استفاده از کد {discount_obj.code} به پایان رسیده است.")
                
                if user in discount_obj.activated_users.all():
                    raise ValueError(f"کاربر {user.phone_number} قبلاً از این کد استفاده کرده است.")
                
                logger.info(f"🟡 مصرف کد تخفیف {discount_obj.code} - remaining_uses قبل: {discount_obj.remaining_uses}")
                
                # کاهش دفعات باقی‌مانده با استفاده از F expression
                RoomDiscountCode.objects.filter(pk=discount_obj.pk).update(
                    remaining_uses=models.F('remaining_uses') - 1
                )
                
                # رفرش برای گرفتن مقدار جدید
                discount_obj.refresh_from_db()
                
                # افزودن کاربر به activated_users (اگر از قبل نیست)
                if user not in discount_obj.activated_users.all():
                    discount_obj.activated_users.add(user)
                
                logger.info(f"🟢 کد تخفیف {discount_obj.code} مصرف شد - remaining_uses بعد: {discount_obj.remaining_uses}")
                
                return True
                
        except Exception as e:
            logger.error(f"🔴 خطا در مصرف کد تخفیف {self.code}: {str(e)}")
            raise

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_uses = self.usage_limit  # اطمینان از تنظیم اولیه
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("کد تخفیف اتاق")
        verbose_name_plural = _("کد تخفیف باشگاه مشتری برای اتاق‌ها")


# کد تخفیف باشگاه مشتریان برای مراکز خرید
class ShoppingCenterDiscountCode(models.Model):
    shopping_center_name = models.CharField(
        max_length=100,
        verbose_name=_("نام مرکز خرید")
    )
    shopping_center_image = models.ImageField(
        upload_to='shopping_centers/',
        null=True,
        blank=True,
        verbose_name=_("لوگو مرکز خرید"),
        help_text=_("تصویر مرکز خرید را آپلود کنید.")
    )
    discount_value = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d+$', message=_("فقط مقادیر عددی مجاز هستند."))],
        verbose_name=_("مقدار تخفیف"),
        help_text=_("مقدار تخفیف را به تومان وارد کنید (فقط عدد).")
    )
    users = models.ManyToManyField(
        BaseUser,
        related_name='targeted_shopping_discount_codes',
        verbose_name=_("کاربران"),
        blank=True,
        help_text=_("کاربرانی که این کد تخفیف برای آن‌ها هدف‌گذاری شده است.")
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        verbose_name=_("کد تخفیف"),
        help_text=_("کد تخفیف ۸ رقمی را وارد کنید.")
    )
    required_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز مورد نیاز"),
        help_text=_("حداقل امتیازی که کاربر باید داشته باشد تا بتواند از کد استفاده کند")
    )
    user_level = models.ForeignKey(
        UserLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shopping_discount_codes',
        verbose_name=_("سطح کاربری"),
        help_text=_("سطوح کاربری که این کد تخفیف برای آن‌ها قابل استفاده است. اگر خالی باشد، برای همه سطوح اعمال می‌شود.")
    )
    expires_at = jmodels.jDateField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ انقضا (شمسی)")
    )
    activation_rules = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("قوانین فعال‌سازی"),
        help_text=_("می‌توانید قوانینی برای نحوه فعال‌سازی این کد وارد کنید.")
    )
    activated_users = models.ManyToManyField(
        BaseUser,
        blank=True,
        related_name='activated_shopping_discount_codes',
        verbose_name=_("کاربران فعال‌کننده"),
        help_text=_("کاربرانی که این کد را فعال کرده‌اند.")
    )

    def __str__(self):
        return f"{self.code} - {self.discount_value} - {self.shopping_center_name}"

    def get_users_with_names(self):
        result = []
        for user in self.users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def get_activated_users_with_names(self):
        result = []
        for user in self.activated_users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    class Meta:
        verbose_name = _("کد تخفیف مرکز خرید")
        verbose_name_plural = _("کدهای تخفیف باشگاه مشتری برای مراکز خرید")


# کد تخفیف باشگاه مشتریان برای هتل‌ها
class HotelDiscountCode(models.Model):
    hotel = models.ForeignKey(
        'reservation.Hotel',
        on_delete=models.CASCADE,
        related_name='discount_codes',
        verbose_name=_("هتل"),
        help_text=_("هتلی که این کد تخفیف برای تمام اتاق‌های آن اعمال می‌شود.")
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[RegexValidator(r'^\d+$', message=_("فقط مقادیر عددی مجاز هستند."))],
        verbose_name=_("مقدار تخفیف"),
        help_text=_("مقدار تخفیف را به تومان وارد کنید (فقط عدد).")
    )
    users = models.ManyToManyField(
        BaseUser,
        related_name='targeted_hotel_discount_codes',
        verbose_name=_("کاربران"),
        blank=True,
        help_text=_("کاربرانی که این کد تخفیف برای آن‌ها هدف‌گذاری شده است.")
    )
    code = models.CharField(
        max_length=8,
        unique=True,
        verbose_name=_("کد تخفیف"),
        help_text=_("کد تخفیف ۸ رقمی را وارد کنید.")
    )
    usage_limit = models.PositiveIntegerField(
        default=1,
        verbose_name=_("حداکثر دفعات استفاده"),
        help_text=_("تعداد کل دفعات مجاز استفاده از این کد تخفیف (ثابت)")
    )
    remaining_uses = models.PositiveIntegerField(
        default=0,
        verbose_name=_("دفعات باقی‌مانده"),
        help_text=_("تعداد دفعات باقی‌مانده برای استفاده از این کد تخفیف")
    )
    required_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز مورد نیاز"),
        help_text=_("حداقل امتیازی که کاربر باید داشته باشد تا بتواند از کد استفاده کند")
    )
    user_level = models.ForeignKey(
        UserLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='hotel_discount_codes',
        verbose_name=_("سطح کاربری"),
        help_text=_("سطوح کاربری که این کد تخفیف برای آن‌ها قابل استفاده است. اگر خالی باشد، برای همه سطوح اعمال می‌شود.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد")
    )
    expires_at = jmodels.jDateField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ انقضا (شمسی)")
    )
    activation_rules = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("قوانین فعال‌سازی"),
        help_text=_("می‌توانید قوانینی برای نحوه فعال‌سازی این کد وارد کنید.")
    )
    activated_users = models.ManyToManyField(
        BaseUser,
        related_name='activated_hotel_discount_codes',
        verbose_name=_("کاربران استفاده‌کننده"),
        blank=True,
        help_text=_("کاربرانی که از این کد تخفیف برای رزرو استفاده کرده‌اند.")
    )

    def __str__(self):
        return f"{self.code} - {self.discount_value} - {self.hotel.name}"

    def get_users_with_names(self):
        result = []
        for user in self.users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def get_activated_users_with_names(self):
        result = []
        for user in self.activated_users.select_related('natural_profile').all():
            profile = getattr(user, 'natural_profile', None)
            if profile and (profile.first_name or profile.last_name):
                full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                result.append(f"{user.phone_number} - {full_name}")
            else:
                result.append(user.phone_number)
        return result

    def consume_discount_for_user(self, user):
        """
        متد یکپارچه برای مصرف کد تخفیف - کاهش remaining_uses و افزودن کاربر
        """
        try:
            with transaction.atomic():
                discount_obj = HotelDiscountCode.objects.select_for_update().get(pk=self.pk)
                
                if discount_obj.remaining_uses <= 0:
                    raise ValueError(f"تعداد دفعات استفاده از کد {discount_obj.code} به پایان رسیده است.")
                
                if user in discount_obj.activated_users.all():
                    raise ValueError(f"کاربر {user.phone_number} قبلاً از این کد استفاده کرده است.")
                
                logger.info(f"🟡 مصرف کد تخفیف {discount_obj.code} - remaining_uses قبل: {discount_obj.remaining_uses}")
                
                # کاهش دفعات باقی‌مانده با استفاده از F expression
                HotelDiscountCode.objects.filter(pk=discount_obj.pk).update(
                    remaining_uses=models.F('remaining_uses') - 1
                )
                
                # رفرش برای گرفتن مقدار جدید
                discount_obj.refresh_from_db()
                
                # افزودن کاربر به activated_users (اگر از قبل نیست)
                if user not in discount_obj.activated_users.all():
                    discount_obj.activated_users.add(user)
                
                logger.info(f"🟢 کد تخفیف {discount_obj.code} مصرف شد - remaining_uses بعد: {discount_obj.remaining_uses}")
                
                return True
                
        except Exception as e:
            logger.error(f"🔴 خطا در مصرف کد تخفیف {self.code}: {str(e)}")
            raise

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_uses = self.usage_limit  # اطمینان از تنظیم اولیه
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("کد تخفیف هتل")
        verbose_name_plural = _("کدهای تخفیف باشگاه مشتری برای هتل‌ها")


# امتیاز باشگاه مشتری کاربران
class CustomerClubPoint(models.Model):
    user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='customer_points',
        verbose_name=_("کاربر")
    )

    points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز فعلی")
    )

    def __str__(self):
        return f"{self.user} - {self.points} امتیاز"

    class Meta:
        verbose_name = _("امتیاز باشگاه مشتریان کاربر")
        verbose_name_plural = _("امتیازهای باشگاه مشتریان کاربران")


# لیست جوایز فعال شده کاربران
class DiscountActivationRecord(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('room', _('تخفیف اتاق')),
        ('shopping_center', _('تخفیف مرکز خرید')),
        ('hotel', _('تخفیف هتل')),
    ]

    user = models.ForeignKey(
        BaseUser,
        on_delete=models.CASCADE,
        verbose_name=_("کاربر فعال‌کننده"),
        related_name='discount_activations'
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name=_("نوع کد تخفیف"),
    )

    room_discount_code = models.ForeignKey(
        RoomDiscountCode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("کد تخفیف اتاق"),
        related_name='activation_records'
    )

    shopping_discount_code = models.ForeignKey(
        ShoppingCenterDiscountCode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("کد تخفیف مرکز خرید"),
        related_name='activation_records'
    )

    hotel_discount_code = models.ForeignKey(
        HotelDiscountCode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("کد تخفیف هتل"),
        related_name='activation_records'
    )

    activated_at = jmodels.jDateField(
        auto_now_add=True,
        verbose_name=_("تاریخ فعال‌سازی (شمسی)")
    )

    reward_claimed = models.BooleanField(
        default=False,
        verbose_name=_("جایزه استفاده شده؟"),
        help_text=_("نمایش وضعیت جایزه استفاده شده توسط کاربر")
    )

    class Meta:
        verbose_name = _("جوایز دریافتی")
        verbose_name_plural = _("لیست دریافت جوایز کاربران")
        ordering = ['-activated_at']

    def __str__(self):
        code = self.room_discount_code or self.shopping_discount_code or self.hotel_discount_code
        code_str = code.code if code else '—'
        return f"{self.user} - {self.get_discount_type_display()} - {code_str} - {self.activated_at}"

    def mark_as_used(self):
        """علامت‌گذاری رکورد به عنوان استفاده شده"""
        self.reward_claimed = True
        self.save(update_fields=['reward_claimed'])
        logger.info(f"رکورد فعال‌سازی {self.id} به عنوان استفاده شده علامت‌گذاری شد")