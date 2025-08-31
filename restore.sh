#!/bin/bash

BACKUP_DIR=/var/backups/sf24_9xkLp7

# آرگومان اول: فایل SQL
DB_FILE=$1
# آرگومان دوم: فایل مدیا
MEDIA_FILE=$2

# چک کردن اگر dummy باشد، skip کند
if [ "$DB_FILE" != "dummy_db" ] && [ -z "$DB_FILE" ]; then
  echo "❌ مسیر فایل بکاپ دیتابیس را بدهید"
  exit 1
fi

if [ "$MEDIA_FILE" != "dummy_media" ] && [ -z "$MEDIA_FILE" ]; then
  echo "❌ مسیر فایل بکاپ مدیا را بدهید"
  exit 1
fi

# 1. ریستور دیتابیس اگر dummy نباشد
if [ "$DB_FILE" != "dummy_db" ]; then
  echo "📦 ریستور دیتابیس..."
  cat $DB_FILE | docker exec -i postgres_db psql -U postgres safarname24
fi

# 2. ریستور مدیا اگر dummy نباشد
if [ "$MEDIA_FILE" != "dummy_media" ]; then
  echo "🖼 ریستور مدیا..."
  tar -xzf $MEDIA_FILE -C /var/hotelscript-v2
fi

echo "✅ ریستور انجام شد"