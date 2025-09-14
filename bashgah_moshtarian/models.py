from django.db import models
from django.core.validators import RegexValidator
from reservation.models import Room
from authentication.models import BaseUser
from config.models import UserLevel
from django_jalali.db import models as jmodels
from django.utils.translation import gettext_lazy as _



# مدل کد تخفیف باشگاه مشتری برای اتاق ها 
class RoomDiscountCode(models.Model):
    room = models.ForeignKey(
        Room,
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
        help_text=_("تعداد دفعات مجاز استفاده از این کد تخفیف")
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
        verbose_name=_("کاربران فعال‌کننده"),
        blank=True,
        help_text=_("کاربرانی که این کد را فعال کرده‌اند.")
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

    def apply_discount(self, user):
        """
        متد برای اعمال کد تخفیف و کاهش usage_limit و remaining_uses
        """
        if self.remaining_uses <= 0:
            raise ValueError("تعداد دفعات استفاده از این کد به پایان رسیده است.")
        if user in self.activated_users.all():
            raise ValueError("این کاربر قبلاً از این کد استفاده کرده است.")
        
        # کاهش هر دو فیلد
        self.usage_limit -= 1
        self.remaining_uses -= 1
        self.activated_users.add(user)
        self.save()

    def save(self, *args, **kwargs):
        # تنظیم remaining_uses به مقدار اولیه usage_limit اگر هنوز ست نشده باشد
        if not self.pk and self.remaining_uses == 0:
            self.remaining_uses = self.usage_limit
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
        
        
        
        
        

#لیست جوایز فعال شده کاربران 
class DiscountActivationRecord(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('room', _('تخفیف اتاق')),
        ('shopping_center', _('تخفیف مرکز خرید')),
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

    activated_at = jmodels.jDateField(
        auto_now_add=True,
        verbose_name=_("تاریخ فعال‌سازی (شمسی)")
    )

    reward_claimed = models.BooleanField(
        default=False,
        verbose_name=_("جایزه دریافت شده؟"),
        help_text=_("نمایش وضعیت دریافت جایزه توسط کاربر")
    )

    class Meta:
        verbose_name = _("جوایز دریافتی")
        verbose_name_plural = _("لیست دریافت جوایز کاربران")
        ordering = ['-activated_at']

    def __str__(self):
        code = self.room_discount_code or self.shopping_discount_code
        code_str = code.code if code else '—'
        return f"{self.user} - {self.get_discount_type_display()} - {code_str} - {self.activated_at}"