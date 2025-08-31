#!/bin/bash

# مسیر پوشه بکاپ
BACKUP_DIR=/var/backups/sf24_9xkLp7
PROJECT_DIR=/var/hotelscript-v2
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# ایجاد پوشه بکاپ اگر وجود نداشته باشد
mkdir -p "$BACKUP_DIR"
if [ ! -w "$BACKUP_DIR" ]; then
  echo "❌ دسترسی نوشتن به $BACKUP_DIR وجود ندارد"
  exit 1
fi

# ---------------- بکاپ دیتابیس ----------------
echo "📦 در حال بکاپ گرفتن از دیتابیس..."
DB_FILE="$BACKUP_DIR/db_$DATE.sql"
if ! docker exec -i postgres_db pg_dump -U postgres safarname24 > "$DB_FILE" 2>/tmp/backup_db_error.log; then
  echo "❌ خطا در بکاپ دیتابیس: $(cat /tmp/backup_db_error.log)"
  exit 1
fi
echo "✅ بکاپ دیتابیس ذخیره شد: $DB_FILE"

# ---------------- بکاپ مدیا ----------------
MEDIA_SRC="$PROJECT_DIR/media"
MEDIA_FILE="$BACKUP_DIR/media_$DATE.tar.gz"

if [ ! -d "$MEDIA_SRC" ]; then
  echo "❌ پوشه $MEDIA_SRC وجود ندارد"
  exit 1
fi

echo "🖼 در حال بکاپ گرفتن از مدیا..."
if ! tar -czf "$MEDIA_FILE" -C "$PROJECT_DIR" media 2>/tmp/backup_media_error.log; then
  echo "❌ خطا در بکاپ مدیا: $(cat /tmp/backup_media_error.log)"
  exit 1
fi
echo "✅ بکاپ مدیا ذخیره شد: $MEDIA_FILE"

echo "✅ بکاپ کامل انجام شد: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
