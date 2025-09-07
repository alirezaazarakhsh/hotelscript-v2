from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction

class UserManager(BaseUserManager):
    """
    UserManager برای کاربران OTP-based
    """

    def create_user(self, phone_number=None, **other_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است.')

        # ایمپورت داخلی برای جلوگیری از circular import
        from authentication.models import NaturalProfile
        from config.models import UserLevel

        # ابتدا بررسی می‌کنیم کاربر قبلا وجود دارد یا نه
        user, created = self.model.objects.get_or_create(
            phone_number=phone_number,
            defaults=other_fields
        )

        if created:
            # ست کردن پسورد غیرقابل استفاده
            user.set_unusable_password()
            user.save(using=self._db)

            # ست کردن پروفایل حقیقی و سطح میهمان فقط برای کاربر جدید
            guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')
            NaturalProfile.objects.get_or_create(
                base_user=user,
                defaults={
                    'first_name': 'میهمان',
                    'last_name': 'عزیز',
                    'level': guest_level
                }
            )

        return user

    def create_superuser(self, **other_fields):
        raise NotImplementedError('Use the SuperUser model to create superusers.')

    def get_by_phone(self, phone):
        return self.model.objects.get(phone_number=phone)

    def get_by_phone_or_create(self, phone):
        from finance.models import Wallet
        from bashgah_moshtarian.models import CustomerClubPoint
        try:
            return self.get_by_phone(phone)
        except self.model.DoesNotExist:
            with transaction.atomic():
                user = self.create_user(phone_number=phone)
                Wallet.objects.get_or_create(user=user, defaults={'balance': 0})
                CustomerClubPoint.objects.get_or_create(user=user, defaults={'points': 0})
                return user