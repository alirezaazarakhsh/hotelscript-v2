import os
from dotenv import load_dotenv

# ================= بارگذاری متغیرهای محیطی =================
ENV_PATH = os.getenv("ENV_PATH", "/app/hotel_bot/.env")
if not os.path.exists(ENV_PATH):
    raise FileNotFoundError(f"⚠️ فایل .env پیدا نشد در مسیر {ENV_PATH}. لطفاً فایل .env را تنظیم کنید.")

load_dotenv(dotenv_path=ENV_PATH)

# بررسی متغیرهای محیطی ضروری
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN در فایل .env تعریف نشده است. لطفاً یک توکن معتبر تنظیم کنید.")

# ================= تنظیمات پروژه =================
PROJECT_DIR = os.getenv("PROJECT_DIR", "/app")
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", os.path.join(PROJECT_DIR, "backups/database"))
MEDIA_BACKUP_DIR = os.getenv("MEDIA_BACKUP_DIR", os.path.join(PROJECT_DIR, "backups/media"))
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/media/")

# ایجاد دایرکتوری‌های بکاپ در صورت عدم وجود
for directory in [DB_BACKUP_DIR, MEDIA_BACKUP_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# مدیریت SUPER_ADMINS
SUPER_ADMINS = []
try:
    SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x]
    if not SUPER_ADMINS:
        print("⚠️ SUPER_ADMINS در فایل .env خالی است. لطفاً حداقل یک سوپرادمین تعریف کنید.")
except ValueError as e:
    print(f"⚠️ خطا در تعریف SUPER_ADMINS: {str(e)}. لطفاً IDهای معتبر (عدد) وارد کنید.")

MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", 7))  # حداکثر تعداد بکاپ‌های نگهداری‌شده
ADMINS_FILE = os.path.join(PROJECT_DIR, "admins.json")  # فایل برای ذخیره ادمین‌ها و گروه‌ها

# ================= مجوزها =================
PERMISSIONS = [
    'backup_db',        # بکاپ‌گیری از دیتابیس
    'backup_media',     # بکاپ‌گیری از مدیا
    'backup_info',      # مشاهده اطلاعات بکاپ
    'support',          # دسترسی به پشتیبانی
    'manage_admins',    # مدیریت ادمین‌ها و گروه‌ها
    'wallet_charge',    # شارژ کیف پول
    'view_balance',     # مشاهده موجودی کیف پول
    'manage_wallet',    # مدیریت کیف پول دیگران (برای سوپرادمین‌ها)
    'edit_profile',     # ویرایش پروفایل کاربر
]

# نمایش فارسی مجوزها با توضیحات
PERM_DISPLAY = {
    'backup_db': {
        'label': 'بکاپ دیتابیس',
        'desc': 'اجازه بکاپ‌گیری از پایگاه داده (فایل SQL). این گزینه برای حفظ داده‌های اصلی سایت ضروری است.'
    },
    'backup_media': {
        'label': 'بکاپ مدیا',
        'desc': 'اجازه بکاپ‌گیری از فایل‌های رسانه‌ای (فشرده tar.gz). شامل تصاویر، ویدیوها و سایر فایل‌های آپلود شده.'
    },
    'backup_info': {
        'label': 'اطلاعات بکاپ',
        'desc': 'نمایش راهنما و توضیحات در مورد فرآیند بکاپ‌گیری.'
    },
    'support': {
        'label': 'پشتیبانی',
        'desc': 'دسترسی به بخش پشتیبانی و تماس با ادمین.'
    },
    'manage_admins': {
        'label': 'مدیریت ادمین‌ها',
        'desc': 'مدیریت کاربران ادمین و گروه‌های دسترسی. فقط برای سوپرادمین‌ها.'
    },
    'wallet_charge': {
        'label': 'شارژ کیف پول',
        'desc': 'اجازه شارژ کیف پول از طریق درگاه پرداخت یا کارت به کارت.'
    },
    'view_balance': {
        'label': 'مشاهده موجودی کیف پول',
        'desc': 'نمایش موجودی فعلی کیف پول کاربر.'
    },
    'manage_wallet': {
        'label': 'مدیریت کیف پول دیگران',
        'desc': 'اجازه شارژ کیف پول کاربران دیگر توسط سوپرادمین‌ها.'
    },
    'edit_profile': {
        'label': 'ویرایش پروفایل',
        'desc': 'اجازه تغییر مشخصات پروفایل شخصی مانند نام، نام خانوادگی، کد ملی و اطلاعات تماس.'
    },
}