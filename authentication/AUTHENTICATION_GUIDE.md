# راهنمای مدیریت سیستم احراز هویت

## 📚 ساختار سیستم

### 1. کاربران عادی (NaturalProfile)

- کاربران معمولی سایت
- ورود با OTP (کد یکبار مصرف)
- دسترسی به پنل کاربری

### 2. ادمین‌های سایت (Admin)

- مدیران سایت با دسترسی‌های محدود
- **قابل مدیریت از پنل ادمین جنگو**
- می‌توانید از کاربران عادی، ادمین بسازید
- می‌توانید گروه‌ها و دسترسی‌ها (permissions) تعیین کنید
- ورود با OTP به پنل کاربری (مثل کاربران عادی)
- **نمی‌توانند به پنل ادمین جنگو دسترسی داشته باشند**

### 3. ادمین‌های جنگو (SuperUser)

- دسترسی کامل به سیستم
- **فقط از طریق ترمینال قابل مدیریت**
- ورود با شماره موبایل + رمز عبور به پنل ادمین جنگو

---

## 🔧 دستورات مدیریتی

### ساخت یا تنظیم رمز SuperUser

```bash
# در محیط محلی
python3 manage.py create_superuser_admin --phone 09123456789 --password your_strong_password

# در Docker
docker exec -it django_app python manage.py create_superuser_admin --phone 09123456789 --password your_strong_password
```

**مثال:**

```bash
python3 manage.py create_superuser_admin --phone 09123456789 --password Admin@123456
```

### لیست کردن SuperUser ها

```bash
# در محیط محلی
python3 manage.py list_superusers

# در Docker
docker exec -it django_app python manage.py list_superusers
```

---

## 📋 نحوه کار با سیستم

### ساخت ادمین سایت (Admin)

1. وارد پنل ادمین جنگو شوید (با حساب SuperUser)
2. به بخش `Authentication and Authorization > کاربران` بروید
3. کاربر مورد نظر را پیدا کنید
4. گروه‌ها (Groups) و دسترسی‌ها (Permissions) را تنظیم کنید
5. به بخش `Authentication > ادمین‌ها` بروید و یک Admin برای آن کاربر بسازید

### تنظیم دسترسی‌ها

1. به بخش `Authentication and Authorization > Groups` بروید
2. گروه جدید بسازید (مثلاً "مدیر محتوا" یا "پشتیبان")
3. دسترسی‌های مورد نیاز را انتخاب کنید
4. کاربران را به گروه اضافه کنید

---

## 🔐 امنیت

- ❌ **SuperUser را از پنل ادمین حذف کردیم** - فقط از ترمینال قابل مدیریت
- ✅ **Admin ها رمز عبور ندارند** - با OTP وارد می‌شوند
- ✅ **جداسازی کامل بین کاربران، ادمین‌های سایت و ادمین‌های جنگو**

---

## 🚀 نصب در Production

```bash
# در سرور
cd /path/to/project
git pull
docker exec -it django_app python manage.py migrate
docker-compose restart web

# ساخت SuperUser در سرور
docker exec -it django_app python manage.py create_superuser_admin --phone 09123456789 --password your_password
```

---

## ⚠️ نکات مهم

1. همیشه از رمز عبور قوی برای SuperUser استفاده کنید
2. شماره موبایل SuperUser را در جای امن نگه دارید
3. از دستور `list_superusers` برای بررسی لیست SuperUser ها استفاده کنید
4. Admin ها نمی‌توانند به پنل ادمین جنگو دسترسی داشته باشند
