from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from authentication.models import AppGroup


class Command(BaseCommand):
    help = 'ساخت گروه‌های دسترسی و گروه‌بندی اپلیکیشن‌های پیش‌فرض'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('🚀 شروع ساخت گروه‌های پیش‌فرض...'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # ساخت گروه‌بندی اپلیکیشن‌ها
        app_groups_data = [
            {
                'name': 'content_management',
                'display_name': 'مدیریت محتوا',
                'icon': '📝',
                'order': 1,
                'description': 'بلاگ، اخبار، صفحات'
            },
            {
                'name': 'financial',
                'display_name': 'مالی',
                'icon': '💰',
                'order': 2,
                'description': 'کیف پول، تراکنش‌ها، فاکتورها'
            },
            {
                'name': 'user_management',
                'display_name': 'مدیریت کاربران',
                'icon': '👥',
                'order': 3,
                'description': 'کاربران، پروفایل‌ها، دسترسی‌ها'
            },
            {
                'name': 'settings',
                'display_name': 'تنظیمات',
                'icon': '⚙️',
                'order': 4,
                'description': 'پیکربندی سیستم، تنظیمات عمومی'
            },
            {
                'name': 'communication',
                'display_name': 'ارتباطات',
                'icon': '💬',
                'order': 5,
                'description': 'پیامک، ایمیل، نوتیفیکیشن'
            },
        ]

        for ag_data in app_groups_data:
            ag, created = AppGroup.objects.get_or_create(
                name=ag_data['name'],
                defaults={
                    'display_name': ag_data['display_name'],
                    'icon': ag_data['icon'],
                    'order': ag_data['order'],
                    'description': ag_data['description']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ گروه اپلیکیشن "{ag.display_name}" ساخته شد'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ گروه اپلیکیشن "{ag.display_name}" از قبل وجود دارد'))

        # ساخت گروه‌های دسترسی
        self.stdout.write('')
        groups_permissions = {
            'مدیر محتوا': {
                'apps': ['blog', 'config'],
                'permissions': ['add', 'change', 'view']
            },
            'مدیر مالی': {
                'apps': ['finance', 'bashgah_moshtarian'],
                'permissions': ['add', 'change', 'view', 'delete']
            },
            'مدیر کاربران': {
                'apps': ['authentication'],
                'models': ['naturalprofile', 'juridicalprofile', 'admin'],
                'permissions': ['add', 'change', 'view']
            },
            'پشتیبان': {
                'apps': ['contact', 'notification', 'chat_api'],
                'permissions': ['add', 'change', 'view']
            },
        }

        for group_name, config in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                # تنظیم دسترسی‌ها
                permissions = []
                for app_label in config.get('apps', []):
                    for perm_codename in config.get('permissions', []):
                        perms = Permission.objects.filter(
                            content_type__app_label=app_label,
                            codename__startswith=perm_codename
                        )
                        permissions.extend(perms)
                
                if permissions:
                    group.permissions.set(permissions)
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ گروه "{group_name}" با {len(permissions)} دسترسی ساخته شد'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ گروه "{group_name}" ساخته شد اما دسترسی‌ای پیدا نشد'
                    ))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ گروه "{group_name}" از قبل وجود دارد'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('✅ عملیات با موفقیت انجام شد'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # نمایش آمار
        self.stdout.write(self.style.SUCCESS(f'📊 تعداد کل گروه‌های دسترسی: {Group.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'📊 تعداد کل گروه‌های اپلیکیشن: {AppGroup.objects.count()}'))
        self.stdout.write('')
