from django.core.management.base import BaseCommand
from authentication.models import BaseUser, SuperUser


class Command(BaseCommand):
    help = 'نمایش لیست ادمین‌های جنگو (SuperUser)'

    def handle(self, *args, **options):
        superusers = SuperUser.objects.select_related('base_user').all()

        if not superusers:
            self.stdout.write(self.style.WARNING('⚠ هیچ SuperUser پیدا نشد'))
            return

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('📋 لیست ادمین‌های جنگو (SuperUser)'))
        self.stdout.write(self.style.SUCCESS('='*70))

        for su in superusers:
            self.stdout.write('')
            self.stdout.write(f'  ID: {su.id}')
            self.stdout.write(f'  📱 شماره موبایل: {su.base_user.phone_number}')
            self.stdout.write(f'  🔐 رمز عبور: {"تنظیم شده ✓" if su.password else "تنظیم نشده ✗"}')
            
            # نمایش نام اگر profile داشته باشد
            if hasattr(su.base_user, 'natural_profile') and su.base_user.natural_profile:
                profile = su.base_user.natural_profile
                name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                if name:
                    self.stdout.write(f'  👤 نام: {name}')
            
            self.stdout.write('  ' + '-'*66)

        self.stdout.write(self.style.SUCCESS(f'\n📊 تعداد کل: {superusers.count()} SuperUser'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
