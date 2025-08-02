from django.db import models
from reservation.models import Room
from authentication.models import BaseUser
from django_jalali.db import models as jmodels
from django.utils.translation import gettext_lazy as _



# مدل کد تخفیف باشگاه مشتری برای اتاق ها 
class RoomDiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', _('مقدار ثابت')),
        ('percent', _('درصدی')),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='discount_codes',
        verbose_name=_("اتاق")
    )

    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent',
        verbose_name=_("نوع تخفیف")
    )

    discount_value = models.PositiveIntegerField(
        verbose_name=_("مقدار تخفیف"),
        help_text=_("اگر درصدی باشد عددی مانند ۱۰ وارد کنید. اگر مقدار ثابت باشد، مبلغ را به تومان وارد کنید.")
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name=_("تخفیف عمومی است؟"),
        help_text=_("در صورت غیرفعال بودن، کد فقط برای یک کاربر خاص فعال خواهد بود.")
    )

    user = models.ForeignKey(
        BaseUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='room_discount_codes',
        verbose_name=_("کاربر"),
        help_text=_("در صورت شخصی بودن کد، یک کاربر مشخص انتخاب کنید.")
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

    required_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز مورد نیاز"),
        help_text=_("حداقل امتیازی که کاربر باید داشته باشد تا بتواند از کد استفاده کند")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد")
    )

    expires_at =  jmodels.jDateField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ انقضا (شمسی)")
    )

    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()} - {self.discount_value}"

    class Meta:
        verbose_name = _("کد تخفیف اتاق")
        verbose_name_plural = _("کد تخفیف باشگاه مشتری برای اتاق‌ها")



# کد تخفیف باشگاه مشتریان برای مراکز خرید 
class ShoppingCenterDiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', _('مقدار ثابت')),
        ('percent', _('درصدی')),
    ]

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

    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent',
        verbose_name=_("نوع تخفیف")
    )

    discount_value = models.PositiveIntegerField(
        verbose_name=_("مقدار تخفیف"),
        help_text=_("اگر درصدی باشد عددی مانند ۱۰ وارد کنید. اگر مقدار ثابت باشد، مبلغ را به تومان وارد کنید.")
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name=_("تخفیف عمومی است؟"),
        help_text=_("در صورت غیرفعال بودن، کد فقط برای یک کاربر خاص فعال خواهد بود.")
    )

    user = models.ForeignKey(
        'authentication.BaseUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shopping_center_discount_codes',
        verbose_name=_("کاربر"),
        help_text=_("در صورت شخصی بودن کد، یک کاربر مشخص انتخاب کنید.")
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

    required_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("امتیاز مورد نیاز"),
        help_text=_("حداقل امتیازی که کاربر باید داشته باشد تا بتواند از کد استفاده کند")
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

    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()} - {self.discount_value} - {self.shopping_center_name}"

    class Meta:
        verbose_name = _("کد تخفیف مرکز خرید")
        verbose_name_plural = _("کدهای تخفیف باشگاه مشتری برای مراکز خرید")