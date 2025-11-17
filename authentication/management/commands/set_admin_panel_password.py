from django.core.management.base import BaseCommand
from authentication.models import BaseUser, Admin


class Command(BaseCommand):
    help = 'تنظیم یا تغییر رمز پنل گرافیکی برای ادمین سایت'

    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, required=True, help='شماره موبایل کاربر (11 رقم)')
        parser.add_argument('--password', type=str, required=True, help='رمز جدید پنل گرافیکی')

    def handle(self, *args, **options):
        phone = options['phone']
        pwd = options['password']
        try:
            user = BaseUser.objects.get(phone_number=phone)
            admin = getattr(user, 'admin', None)
            if not admin:
                self.stdout.write(self.style.ERROR('❌ این کاربر، ادمین سایت نیست'))
                return
            admin.set_panel_password(pwd)
            admin.save(update_fields=['panel_password'])
            self.stdout.write(self.style.SUCCESS('✅ رمز پنل گرافیکی با موفقیت تنظیم شد'))
        except BaseUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ کاربری با این شماره یافت نشد'))
