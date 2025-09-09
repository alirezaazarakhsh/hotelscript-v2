#!/bin/bash
# ===================== مسیرهای ذخیره بکاپ =====================
DB_BACKUP_DIR="/var/lib/backsafarname/alirezaazarakhsh20_gmail.com"
MEDIA_BACKUP_DIR="/var/backups/sf24_9xkLp7"

# ===================== تنظیم نام فایل با زمان شمسی از آرگومان =====================
TIMESTAMP="$2"  # زمان شمسی از Python (مثل 1404-06-16-06-13)
DB_NAME="${DB_NAME:-safarname24}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

# نام فایل‌ها
DB_FILE="$DB_BACKUP_DIR/db_$TIMESTAMP.sql"
MEDIA_FILE="$MEDIA_BACKUP_DIR/media_$TIMESTAMP.tar.gz"

# ===================== ایجاد پوشه‌ها =====================
mkdir -p "$DB_BACKUP_DIR" || { echo "❌ خطا: نمی‌توان $DB_BACKUP_DIR را ایجاد کرد!"; exit 1; }
mkdir -p "$MEDIA_BACKUP_DIR" || { echo "❌ خطا: نمی‌توان $MEDIA_BACKUP_DIR را ایجاد کرد!"; exit 1; }

# ===================== بررسی دسترسی =====================
if [ ! -w "$DB_BACKUP_DIR" ]; then
    echo "❌ خطا: پوشه $DB_BACKUP_DIR قابل نوشتن نیست!"
    exit 1
fi
if [ ! -w "$MEDIA_BACKUP_DIR" ]; then
    echo "❌ خطا: پوشه $MEDIA_BACKUP_DIR قابل نوشتن نیست!"
    exit 1
fi

# ===================== بررسی نوع بکاپ =====================
BACKUP_TYPE="$1"

if [ "$BACKUP_TYPE" == "db" ]; then
    echo "📦 در حال بکاپ گرفتن از دیتابیس..."
    if [ -z "$DB_PASSWORD" ]; then
        echo "❌ خطا: متغیر DB_PASSWORD تنظیم نشده است!"
        exit 1
    fi
    PGPASSWORD="${DB_PASSWORD}" pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$DB_FILE" 2> /tmp/pg_dump_error.log
    if [ $? -eq 0 ]; then
        echo "✅ بکاپ دیتابیس با موفقیت گرفته شد: $DB_FILE"
        chmod 644 "$DB_FILE"  # تنظیم دسترسی فایل برای خواندن
    else
        echo "❌ خطا در بکاپ دیتابیس: $(cat /tmp/pg_dump_error.log)"
        exit 1
    fi

elif [ "$BACKUP_TYPE" == "media" ]; then
    MEDIA_SOURCE_DIR="/app/media"
    if [ -d "$MEDIA_SOURCE_DIR" ]; then
        echo "📦 در حال بکاپ گرفتن از مدیا..."
        tar -czf "$MEDIA_FILE" -C "$MEDIA_SOURCE_DIR" . 2> /tmp/tar_error.log
        if [ $? -eq 0 ]; then
            echo "✅ بکاپ مدیا با موفقیت گرفته شد: $MEDIA_FILE"
            chmod 644 "$MEDIA_FILE"  # تنظیم دسترسی فایل برای خواندن
        else
            echo "❌ خطا در بکاپ مدیا: $(cat /tmp/tar_error.log)"
            exit 1
        fi
    else
        echo "⚠️ پوشه مدیا وجود ندارد: $MEDIA_SOURCE_DIR"
        exit 1
    fi

else
    echo "⚠️ نوع بکاپ نامشخص است! لطفاً 'db' یا 'media' وارد کنید."
    exit 1
fi

echo "🎉 بکاپ $BACKUP_TYPE انجام شد!"