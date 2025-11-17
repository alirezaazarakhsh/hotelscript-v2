from django.core.management.base import BaseCommand
from authentication.models import BaseUser


class Command(BaseCommand):
    help = 'ساخت یا تنظیم رمز عبور برای سوپر یوزر (دسترسی کامل به پنل جنگو)'

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
            help='رمز عبور برای ورود به پنل ادمین جنگو',
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
            # ساخت/یافتن کاربر با راه‌انداز کامل (پروفایل، کیف پول، امتیاز، سطح)
            base_user = BaseUser.objects.get_by_phone_or_create(phone_number)
            self.stdout.write(self.style.SUCCESS(f'✓ کاربر با شماره {phone_number} آماده است'))

            # تنظیم is_superuser
            was_superuser = base_user.is_superuser
            if not base_user.is_superuser:
                base_user.is_superuser = True
                base_user.save(update_fields=['is_superuser'])
                self.stdout.write(self.style.SUCCESS('✓ کاربر به عنوان سوپر یوزر تنظیم شد'))

            # تنظیم رمز عبور در BaseUser
            base_user.set_password(password)
            base_user.save(update_fields=['password'])

            if not was_superuser:
                self.stdout.write(self.style.SUCCESS('✓ سوپر یوزر جدید ساخته شد و رمز عبور تنظیم شد'))
            else:
                self.stdout.write(self.style.SUCCESS('✓ رمز عبور سوپر یوزر به‌روزرسانی شد'))

            self.stdout.write(self.style.SUCCESS('\n' + '='*50))
            self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))
            self.stdout.write(self.style.SUCCESS(f'📱 شماره موبایل: {phone_number}'))
            self.stdout.write(self.style.SUCCESS(f'🔑 رمز عبور: {"*" * len(password)}'))
            self.stdout.write(self.style.SUCCESS('🌐 می‌توانید با این اطلاعات وارد پنل ادمین جنگو شوید'))
            self.stdout.write(self.style.SUCCESS('💡 نکته: این کاربر دسترسی کامل به تمام بخش‌ها دارد'))
            self.stdout.write(self.style.SUCCESS('='*50))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطا: {str(e)}'))
