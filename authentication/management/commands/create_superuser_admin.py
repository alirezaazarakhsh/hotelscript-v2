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

        user, created = BaseUser.objects.get_or_create(phone_number=phone)
        user.set_password(password)
        
        # در BaseUser فیلد is_staff به صورت خودکار از روی is_superuser خوانده می‌شود
        user.is_superuser = True
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ سوپریوزر با شماره {phone} ساخته شد.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ دسترسی سوپریوزر و رمز کاربر {phone} به‌روزرسانی شد.'))