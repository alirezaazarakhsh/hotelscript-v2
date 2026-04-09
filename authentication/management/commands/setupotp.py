from django.core.management.base import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from authentication.models import BaseUser
import qrcode
from io import StringIO


class Command(BaseCommand):
    help = 'Add TOTP device for a user and display QR code'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number of the user')

    def handle(self, *args, **options):
        phone_number = options['phone_number']
        
        try:
            user = BaseUser.objects.get(phone_number=phone_number)
        except BaseUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'\n❌ کاربر با شماره {phone_number} پیدا نشد\n'))
            return
        
        # Check if user already has TOTP device
        existing_devices = TOTPDevice.objects.filter(user=user, confirmed=True)
        if existing_devices.exists():
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.ERROR('⚠️  این کاربر قبلاً OTP فعال دارد!'))
            self.stdout.write('='*70)
            self.stdout.write(f'\n📱 شماره: {phone_number}')
            self.stdout.write(f'🔐 تعداد devices: {existing_devices.count()}')
            for device in existing_devices:
                self.stdout.write(f'\n  - Device ID: {device.id}')
                self.stdout.write(f'    Key: {device.key}')
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.WARNING('💡 برای ساخت OTP جدید، ابتدا OTP قبلی را حذف کنید:'))
            self.stdout.write(f'   python3 manage.py removeotp {phone_number} --all\n')
            return
        
        # Create TOTP device
        device = TOTPDevice.objects.create(
            user=user,
            name='default',
            confirmed=True
        )
        
        # Generate provisioning URI with issuer and account name
        from urllib.parse import quote
        issuer = "safarnameh24.com"
        account = phone_number
        secret = device.key
        uri = f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}&issuer={quote(issuer)}"
        
        self.stdout.write(self.style.SUCCESS(f'\nTOTP device created for {phone_number}'))
        self.stdout.write(f'Device ID: {device.id}')
        self.stdout.write(f'Key: {device.key}\n')
        
        # Generate QR code and save as PNG for better scanning
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("otp-qr.png")
        self.stdout.write(self.style.SUCCESS('✅ فایل QR با نام otp-qr.png ذخیره شد. با موبایل اسکن کنید.'))
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write('🔑 یا این اطلاعات را دستی وارد کنید:')
        self.stdout.write('='*70)
        self.stdout.write(f'Key: {device.key}')
        self.stdout.write(f'Account: {phone_number}')
        self.stdout.write(f'Type: Time-based (TOTP)')
        self.stdout.write('='*70 + '\n')
