#!/usr/bin/env python3
"""
اسکریپت مستقل برای ساخت سوپر یوزر
این فایل را در سرور در مسیر /app اجرا کنید:
python3 create_superuser_fixed.py
"""

import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safarname24.settings')
sys.path.insert(0, '/app')
django.setup()

from authentication.models import BaseUser


def create_superuser():
    print("="*50)
    print("🔧 ساخت سوپر یوزر (دسترسی کامل)")
    print("="*50)
    
    phone_number = input("📱 شماره موبایل (11 رقم): ").strip()
    password = input("🔑 رمز عبور: ").strip()
    
    # بررسی شماره موبایل
    if len(phone_number) != 11 or not phone_number.isdigit():
        print("❌ خطا: شماره موبایل باید 11 رقم باشد")
        return
    
    if len(password) < 6:
        print("❌ خطا: رمز عبور باید حداقل 6 کاراکتر باشد")
        return
    
    try:
        # ساخت/یافتن کاربر
        base_user = BaseUser.objects.get_by_phone_or_create(phone_number)
        print(f"✓ کاربر با شماره {phone_number} آماده است")
        
        # تنظیم is_superuser
        was_superuser = base_user.is_superuser
        if not base_user.is_superuser:
            base_user.is_superuser = True
            base_user.save(update_fields=['is_superuser'])
            print("✓ کاربر به عنوان سوپر یوزر تنظیم شد")
        
        # تنظیم رمز عبور
        base_user.set_password(password)
        base_user.save(update_fields=['password'])
        
        if not was_superuser:
            print("✓ سوپر یوزر جدید ساخته شد و رمز عبور تنظیم شد")
        else:
            print("✓ رمز عبور سوپر یوزر به‌روزرسانی شد")
        
        print("\n" + "="*50)
        print("✅ عملیات با موفقیت انجام شد")
        print(f"📱 شماره موبایل: {phone_number}")
        print(f"🔑 رمز عبور: {'*' * len(password)}")
        print("🌐 می‌توانید با این اطلاعات وارد پنل ادمین جنگو شوید")
        print("💡 نکته: این کاربر دسترسی کامل به تمام بخش‌ها دارد")
        print("="*50)
        
    except Exception as e:
        print(f"❌ خطا: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_superuser()
