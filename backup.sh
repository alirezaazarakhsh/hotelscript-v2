
#!/bin/bash
# ===================== مسیرهای ذخیره بکاپ =====================
DB_BACKUP_DIR="/var/lib/backsafarname/alirezaazarakhsh20_gmail.com"
MEDIA_BACKUP_DIR="/var/backups/sf24_9xkLp7"

# ===================== تنظیم تاریخ و نام فایل =====================
DATE=$(date +%Y-%m-%d_%H-%M-%S)
DB_NAME="${DB_NAME:-safarname24}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-admin}"

# نام فایل‌ها
DB_FILE="$DB_BACKUP_DIR/db_$DATE.sql"
MEDIA_FILE="$MEDIA_BACKUP_DIR/media_$DATE.tar.gz"

# ===================== ایجاد پوشه‌ها در صورت عدم وجود =====================
mkdir -p "$DB_BACKUP_DIR"
mkdir -p "$MEDIA_BACKUP_DIR"

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
BACKUP_TYPE="$1"  # پارامتر ورودی: db یا media

if [ "$BACKUP_TYPE" == "db" ]; then
    echo "📦 در حال بکاپ گرفتن از دیتابیس..."
    PGPASSWORD="$DB_PASSWORD" pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$DB_FILE"
    if [ $? -eq 0 ]; then
        echo "✅ بکاپ دیتابیس با موفقیت گرفته شد: $DB_FILE"
    else
        echo "❌ خطا در بکاپ دیتابیس!"
        exit 1
    fi

elif [ "$BACKUP_TYPE" == "media" ]; then
    MEDIA_SOURCE_DIR="/app/media"
    if [ -d "$MEDIA_SOURCE_DIR" ]; then
        echo "📦 در حال بکاپ گرفتن از مدیا..."
        tar -czf "$MEDIA_FILE" -C "$MEDIA_SOURCE_DIR" .
        if [ $? -eq 0 ]; then
            echo "✅ بکاپ مدیا با موفقیت گرفته شد: $MEDIA_FILE"
        else
            echo "❌ خطا در بکاپ مدیا!"
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
