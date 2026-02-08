from django.core.management.base import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from authentication.models import BaseUser


class Command(BaseCommand):
    help = 'Remove TOTP device from a user'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number of the user')
        parser.add_argument(
            '--all',
            action='store_true',
            help='Remove all TOTP devices for this user',
        )

    def handle(self, *args, **options):
        phone_number = options['phone_number']
        remove_all = options['all']
        
        try:
            user = BaseUser.objects.get(phone_number=phone_number)
        except BaseUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'\n❌ کاربر با شماره {phone_number} پیدا نشد\n'))
            return
        
        devices = TOTPDevice.objects.filter(user=user)
        
        if not devices.exists():
            self.stdout.write(self.style.WARNING(f'\n⚠️  کاربر {phone_number} هیچ OTP فعالی ندارد\n'))
            return
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.WARNING(f'🗑️  حذف OTP برای کاربر {phone_number}'))
        self.stdout.write('='*70 + '\n')
        
        count = devices.count()
        
        if count > 1 and not remove_all:
            self.stdout.write(self.style.WARNING(f'⚠️  این کاربر {count} device دارد:'))
            for device in devices:
                self.stdout.write(f'  - Device ID: {device.id}, Key: {device.key}')
            self.stdout.write('\n💡 برای حذف همه از --all استفاده کنید:')
            self.stdout.write(f'   python3 manage.py removeotp {phone_number} --all\n')
            return
        
        # Delete devices
        deleted_count, _ = devices.delete()
        
        self.stdout.write(self.style.SUCCESS(f'✅ {deleted_count} OTP device حذف شد'))
        self.stdout.write(f'📱 شماره: {phone_number}')
        self.stdout.write(f'👤 نام: {user.name if hasattr(user, "name") else "بدون نام"}')
        self.stdout.write('\n' + '='*70 + '\n')
        self.stdout.write(self.style.NOTICE('💡 برای ایجاد OTP جدید از دستور زیر استفاده کنید:'))
        self.stdout.write(f'   python3 manage.py setupotp {phone_number}\n')
