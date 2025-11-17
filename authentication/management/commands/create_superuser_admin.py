from django.core.management.base import BaseCommand
from authentication.models import BaseUser, SuperUser


class Command(BaseCommand):
    help = 'ساخت یا تنظیم رمز عبور برای ادمین جنگو (SuperUser)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='شماره موبایل کاربر (11 رقم)',
            required=True
        )
        parser.add_argument(
            '--password',
            type=str,
            help='رمز عبور برای ورود به پنل ادمین',
            required=True
        )

    def handle(self, *args, **options):
        phone_number = options['phone']
        password = options['password']

        # بررسی شماره موبایل
        if len(phone_number) != 11 or not phone_number.isdigit():
            self.stdout.write(self.style.ERROR('❌ شماره موبایل باید 11 رقم باشد'))
            return

        try:
            # پیدا کردن یا ساختن BaseUser
            base_user, created = BaseUser.objects.get_or_create(
                phone_number=phone_number
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ کاربر جدید با شماره {phone_number} ساخته شد'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ کاربر با شماره {phone_number} از قبل وجود دارد'))

            # تنظیم is_superuser
            if not base_user.is_superuser:
                base_user.is_superuser = True
                base_user.save()
                self.stdout.write(self.style.SUCCESS('✓ کاربر به عنوان superuser تنظیم شد'))

            # پیدا کردن یا ساختن SuperUser
            superuser, su_created = SuperUser.objects.get_or_create(
                base_user=base_user
            )

            # تنظیم رمز عبور
            superuser.set_password(password)
            superuser.save()

            if su_created:
                self.stdout.write(self.style.SUCCESS('✓ SuperUser جدید ساخته شد و رمز عبور تنظیم شد'))
            else:
                self.stdout.write(self.style.SUCCESS('✓ رمز عبور SuperUser به‌روزرسانی شد'))

            self.stdout.write(self.style.SUCCESS('\n' + '='*50))
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))
            self.stdout.write(self.style.SUCCESS(f'📱 شماره موبایل: {phone_number}'))
            self.stdout.write(self.style.SUCCESS(f'🔑 رمز عبور: {"*" * len(password)}'))
            self.stdout.write(self.style.SUCCESS('🌐 می‌توانید با این اطلاعات وارد پنل ادمین شوید'))
            self.stdout.write(self.style.SUCCESS('='*50))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطا: {str(e)}'))
