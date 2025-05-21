from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, **other_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است.')

        user = self.model(phone_number=phone_number, **other_fields)
        user.save()

        return user

    def create_superuser(self, **other_fields):
        raise NotImplementedError('Use the SuperUser model to create superusers.')
    
    def get_by_phone(self, phone):
        return super(UserManager, self).get_queryset().get(phone_number=phone)
    
    def get_by_phone_or_create(self, phone):
        from finance.models import Wallet
        from user_profile.models import CustomerClub
        try:
            return self.get_by_phone(phone)
        except ObjectDoesNotExist:
            fields = {
                'phone_number': phone
            }
            with transaction.atomic():
                user = self.create_user(**fields)
                Wallet.objects.create(
                    user=user,
                    balance=0,
                )
                CustomerClub.objects.create(
                    user=user,
                    points=0,
                )
                return user
