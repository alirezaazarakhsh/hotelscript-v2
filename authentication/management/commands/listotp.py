from django.core.management.base import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from authentication.models import BaseUser


class Command(BaseCommand):
    help = 'List all users with TOTP enabled'

    def handle(self, *args, **options):
        devices = TOTPDevice.objects.filter(confirmed=True).select_related('user')
        
        if not devices.exists():
            self.stdout.write(self.style.WARNING('\n⚠️  هیچ کاربری با OTP فعال پیدا نشد\n'))
            return
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📱 لیست کاربران با OTP فعال'))
        self.stdout.write('='*70 + '\n')
        
        for device in devices:
            user = device.user
            self.stdout.write(f'  🔐 Device ID: {device.id}')
            self.stdout.write(f'  📱 شماره: {user.phone_number}')
            self.stdout.write(f'  👤 نام: {user.name if hasattr(user, "name") else "بدون نام"}')
            self.stdout.write(f'  🔑 Key: {device.key}')
            self.stdout.write(f'  📅 تاریخ ایجاد: {device.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(device, "created_at") else "N/A"}')
            self.stdout.write(f'  ✅ وضعیت: فعال')
            self.stdout.write('  ' + '-'*66 + '\n')
        
        self.stdout.write(self.style.SUCCESS(f'📊 تعداد کل: {devices.count()} کاربر'))
        self.stdout.write('='*70 + '\n')
        self.stdout.write(self.style.NOTICE('💡 برای حذف OTP از دستور زیر استفاده کنید:'))
        self.stdout.write('   python3 manage.py removeotp <phone_number>\n')
