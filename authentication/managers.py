from django.contrib.auth.base_user import BaseUserManager
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model

class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, **other_fields):
        if not phone_number:
            raise ValueError('شماره موبایل الزامی است.')

        user = self.model(phone_number=phone_number, **other_fields)
        user.set_unusable_password()
        user.save()

        return user
    
    def create_superuser(self, phone_number, password, **other_fields):
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('is_superuser', True)
      
        if other_fields.get('is_staff') is not True:
            raise ValueError('Superuser must be assigned to is_staff=True')
       
        if other_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must be assigned to is_superuser=True')
        
        user = self.create_user(phone_number=phone_number, **other_fields)
        user.set_password(password)
        user.save()
        return user
    
    def get_by_phone(self, phone):
        return super(UserManager, self).get_queryset().get(phone_number=phone)
    
    def get_by_phone_or_create(self, phone):
        try:
            return self.get_by_phone(phone)
        except ObjectDoesNotExist:
            fields = {
                'phone_number': phone
            }
            return self.create_user(**fields)
