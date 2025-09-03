import os
from dotenv import load_dotenv

# ================= بارگذاری متغیرهای محیطی =================
ENV_PATH = "/app/hotel_bot/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"⚠️ فایل .env پیدا نشد در مسیر {ENV_PATH}")

PROJECT_DIR = os.getenv("PROJECT_DIR", "/var/hotelscript-v2")
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", "/var/lib/backsafarname/alirezaazarakhsh20_gmail.com")
MEDIA_BACKUP_DIR = os.getenv("MEDIA_BACKUP_DIR", "/var/backups/sf24_9xkLp7")
TOKEN = os.getenv("BOT_TOKEN")
# مدیریت SUPER_ADMINS برای جلوگیری از خطا در صورت خالی بودن
SUPER_ADMINS = [int(x) for x in os.getenv("SUPER_ADMINS", "").split(",") if x]
MAX_BACKUPS = 7
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "https://cps.safarnameh24.com/sf24_9xkLp7/")

ADMINS_FILE = "admins.json"  # فایل برای ذخیره ادمین‌ها و گروه‌ها

# مجوزهای موجود
PERMISSIONS = [
    'backup_db',
    'backup_media',
    'list_backups',
    'delete_backups',
    'restore_db',
    'restore_media',
    'backup_info',
    'support',
    'manage_admins'
]

# نمایش فارسی مجوزها با توضیحات
PERM_DISPLAY = {
    'backup_db': {'label': 'بکاپ دیتابیس', 'desc': 'اجازه بکاپ‌گیری از پایگاه داده (فایل SQL). این گزینه برای حفظ داده‌های اصلی سایت ضروری است.'},
    'backup_media': {'label': 'بکاپ مدیا', 'desc': 'اجازه بکاپ‌گیری از فایل‌های رسانه‌ای (فشرده tar.gz). شامل تصاویر، ویدیوها و سایر فایل‌های آپلود شده.'},
    'list_backups': {'label': 'لیست بکاپ‌ها', 'desc': 'نمایش لیست بکاپ‌های موجود. مفید برای بررسی تاریخچه بکاپ‌ها.'},
    'delete_backups': {'label': 'حذف بکاپ‌ها', 'desc': 'حذف بکاپ‌های قدیمی یا غیرضروری. توجه: این عمل برگشت‌ناپذیر است.'},
    'restore_db': {'label': 'ریستور دیتابیس', 'desc': 'بازگردانی بکاپ دیتابیس به وضعیت فعلی. ممکن است داده‌های فعلی را جایگزین کند.'},
    'restore_media': {'label': 'ریستور مدیا', 'desc': 'بازگردانی بکاپ فایل‌های رسانه‌ای. ممکن است فایل‌های فعلی را جایگزین کند.'},
    'backup_info': {'label': 'اطلاعات بکاپ', 'desc': 'نمایش راهنما و توضیحات در مورد فرآیند بکاپ‌گیری.'},
    'support': {'label': 'پشتیبانی', 'desc': 'دسترسی به بخش پشتیبانی و تماس با ادمین.'},
    'manage_admins': {'label': 'مدیریت ادمین‌ها', 'desc': 'مدیریت کاربران ادمین و گروه‌های دسترسی. فقط برای سوپرادمین‌ها.'}
}