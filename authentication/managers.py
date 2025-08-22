from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from authentication.models import NaturalProfile
from config.models import UserLevel
from finance.models import Wallet
from bashgah_moshtarian.models import CustomerClubPoint

class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, **other_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است.')

        user = self.model(phone_number=phone_number, **other_fields)
        user.set_unusable_password()  # چون پسورد سنتی نداریم
        user.save(using=self._db)

        # ساخت پروفایل حقیقی و ست کردن سطح میهمان
        guest_level, _ = UserLevel.objects.get_or_create(title='میهمان')
        NaturalProfile.objects.create(
            base_user=user,
            first_name='میهمان',
            last_name='.',
            level=guest_level
        )

        return user

    def create_superuser(self, phone_number, **other_fields):
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number=phone_number, **other_fields)

    def get_by_phone(self, phone):
        return super(UserManager, self).get_queryset().get(phone_number=phone)

    def get_by_phone_or_create(self, phone):
        try:
            return self.get_by_phone(phone)
        except ObjectDoesNotExist:
            with transaction.atomic():
                user = self.create_user(phone_number=phone)
                Wallet.objects.create(user=user, balance=0)
                CustomerClubPoint.objects.create(user=user, points=0)
                return user
