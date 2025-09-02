#!/bin/bash
# مسیر ذخیره بکاپ دیتابیس
DB_BACKUP_DIR="/var/lib/backsafarname/alirezaazarakhsh20_gmail.com"
# مسیر ذخیره بکاپ مدیا
MEDIA_BACKUP_DIR="${BACKUP_DIR:-/var/backups/sf24_9xkLp7}"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
DB_NAME="${DB_NAME:-safarname24}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

# ایجاد پوشه‌های بکاپ در صورت عدم وجود
mkdir -p "$DB_BACKUP_DIR"
mkdir -p "$MEDIA_BACKUP_DIR"

# بررسی دسترسی به پوشه دیتابیس
if [ ! -w "$DB_BACKUP_DIR" ]; then
    echo "❌ خطا: پوشه $DB_BACKUP_DIR قابل نوشتن نیست!"
    exit 1
fi

# بررسی دسترسی به پوشه مدیا
if [ ! -w "$MEDIA_BACKUP_DIR" ]; then
    echo "❌ خطا: پوشه $MEDIA_BACKUP_DIR قابل نوشتن نیست!"
    exit 1
fi

echo "📦 در حال بکاپ گرفتن از دیتابیس..."

# بکاپ PostgreSQL
PGPASSWORD="${DB_PASSWORD}" pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$DB_BACKUP_DIR/db_$DATE.sql"

if [ $? -eq 0 ]; then
    echo "✅ بکاپ دیتابیس با موفقیت گرفته شد: $DB_BACKUP_DIR/db_$DATE.sql"
else
    echo "❌ خطا در بکاپ دیتابیس!"
    exit 1
fi

# بکاپ فایل‌های مدیا
MEDIA_DIR="/app/media"
if [ -d "$MEDIA_DIR" ]; then
    echo "📦 در حال بکاپ گرفتن از مدیا..."
    zip -r "$MEDIA_BACKUP_DIR/media_$DATE.zip" "$MEDIA_DIR" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ بکاپ مدیا با موفقیت گرفته شد: $MEDIA_BACKUP_DIR/media_$DATE.zip"
    else
        echo "❌ خطا در بکاپ مدیا!"
    fi
else
    echo "⚠️ پوشه مدیا وجود ندارد: $MEDIA_DIR"
fi

echo "🎉 بکاپ کامل انجام شد!"