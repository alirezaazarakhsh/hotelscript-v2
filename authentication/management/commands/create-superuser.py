from django.core.management.base import BaseCommand
from ...models import BaseUser


class Command(BaseCommand):
    help = 'Create a superuser with phone number and password'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number for the superuser',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the superuser',
        )

    def handle(self, *args, **options):
        phone_number = options['phone']
        password = options['password']
        
        if not phone_number:
            phone_number = input("📱 شماره موبایل (11 رقم): ").strip()
        if not password:
            password = input("🔑 رمز عبور: ").strip()
        
        # بررسی شماره موبایل
        if len(phone_number) != 11 or not phone_number.isdigit():
            self.stdout.write(self.style.ERROR("❌ خطا: شماره موبایل باید 11 رقم باشد"))
            return
        
        if len(password) < 6:
            self.stdout.write(self.style.ERROR("❌ خطا: رمز عبور باید حداقل 6 کاراکتر باشد"))
            return
        
        try:
            # ساخت/یافتن کاربر
            base_user = BaseUser.objects.get_by_phone_or_create(phone_number)
            self.stdout.write(f"✓ کاربر با شماره {phone_number} آماده است")
            
            # تنظیم is_superuser
            was_superuser = base_user.is_superuser
            if not base_user.is_superuser:
                base_user.is_superuser = True
                base_user.save(update_fields=['is_superuser'])
                self.stdout.write("✓ کاربر به عنوان سوپر یوزر تنظیم شد")
            
            # تنظیم رمز عبور
            base_user.set_password(password)
            base_user.save(update_fields=['password'])
            
            if not was_superuser:
                self.stdout.write("✓ سوپر یوزر جدید ساخته شد و رمز عبور تنظیم شد")
            else:
                self.stdout.write("✓ رمز عبور سوپر یوزر به‌روزرسانی شد")
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write("✅ عملیات با موفقیت انجام شد")
            self.stdout.write(f"📱 شماره موبایل: {phone_number}")
            self.stdout.write(f"🔑 رمز عبور: {'*' * len(password)}")
            self.stdout.write("🌐 می‌توانید با این اطلاعات وارد پنل ادمین جنگو شوید")
            self.stdout.write("💡 نکته: این کاربر دسترسی کامل به تمام بخش‌ها دارد")
            self.stdout.write("="*50)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ خطا: {str(e)}"))
            import traceback
            traceback.print_exc()
