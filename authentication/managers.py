from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction


class UserManager(BaseUserManager):
    """
    UserManager برای کاربران OTP-based و سوپریوزرها
    """

    def create_user(self, phone_number=None, **other_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است.')

        from authentication.models import NaturalProfile
        from config.models import UserLevel

        user, created = self.model.objects.get_or_create(
            phone_number=phone_number,
            defaults=other_fields
        )

        if created:
            user.set_unusable_password()
            user.save(using=self._db)

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

    def create_superuser(self, phone_number=None, password=None, **other_fields):
        """
        ساخت سوپریوزر با دسترسی کامل به پنل ادمین
        """
        if not phone_number:
            raise ValueError('شماره موبایل برای سوپریوزر الزامی است.')

        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_active', True)

        user, created = self.model.objects.get_or_create(
            phone_number=phone_number,
            defaults=other_fields
        )

        if password:
            user.set_password(password)
        
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)
        return user

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