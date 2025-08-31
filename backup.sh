#!/bin/bash
# مسیر ذخیره بکاپ
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sf24_9xkLp7}"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
DB_NAME="${DB_NAME:-safarname24}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

mkdir -p "$BACKUP_DIR"

echo "📦 در حال بکاپ گرفتن از دیتابیس..."

# بکاپ PostgreSQL
PGPASSWORD="${DB_PASSWORD}" pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$BACKUP_DIR/db_$DATE.sql"

if [ $? -eq 0 ]; then
    echo "✅ بکاپ دیتابیس با موفقیت گرفته شد: $BACKUP_DIR/db_$DATE.sql"
else
    echo "❌ خطا در بکاپ دیتابیس!"
    exit 1
fi

# بکاپ فایل‌های مدیا
MEDIA_DIR="/app/media"
if [ -d "$MEDIA_DIR" ]; then
    echo "📦 در حال بکاپ گرفتن از مدیا..."
    zip -r "$BACKUP_DIR/media_$DATE.zip" "$MEDIA_DIR" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ بکاپ مدیا با موفقیت گرفته شد: $BACKUP_DIR/media_$DATE.zip"
    else
        echo "❌ خطا در بکاپ مدیا!"
    fi
else
    echo "⚠️ پوشه مدیا وجود ندارد: $MEDIA_DIR"
fi

echo "🎉 بکاپ کامل انجام شد!"
