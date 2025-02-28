from django.core.management.base import BaseCommand
from ...models import SuperUser, BaseUser
from django.db import transaction

class Command(BaseCommand):
    help = 'Create a superuser'

    def handle(self, *args, **options):
        phone = input(f'{BaseUser.USERNAME_FIELD}: ')
        password = input('password: ')

        try:
            with transaction.atomic():
                base_user, _created = BaseUser.objects.get_or_create(phone_number=phone)
                super_user = SuperUser(base_user=base_user)
                super_user.set_password(raw_password=password)
                super_user.save()
        except Exception as e:
            self.stdout.write(self.style.ERROR(e))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))
