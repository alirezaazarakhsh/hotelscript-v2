from django.core.management.base import BaseCommand
from authentication.models import BaseUser

class Command(BaseCommand):
    help = 'ساخت یا تنظیم مجدد رمز سوپریوزر (مدیر کل)'

    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, required=True, help='شماره موبایل ادمین')
        parser.add_argument('--password', type=str, required=True, help='رمز عبور ادمین')

    def handle(self, *args, **options):
        phone = options['phone'].strip()
        password = options['password'].strip()

        # چک کردن اینکه آیا کاربر از قبل وجود دارد یا خیر
        user = BaseUser.objects.filter(phone_number=phone).first()
        created = False

        if not user:
            user = BaseUser(phone_number=phone)
            created = True

        # تنظیم پسورد به صورت هش شده پیش از ذخیره سازی
        user.set_password(password)
        user.is_superuser = True
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ سوپریوزر با شماره {phone} با موفقیت ساخته شد.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ دسترسی سوپریوزر و رمز کاربر {phone} با موفقیت به‌روزرسانی شد.'))