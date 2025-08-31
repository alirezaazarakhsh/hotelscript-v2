#!/bin/bash

BACKUP_DIR=/var/backups/safarnameh

# آرگومان اول: فایل SQL
DB_FILE=$1
# آرگومان دوم: فایل مدیا
MEDIA_FILE=$2

if [ -z "$DB_FILE" ] || [ -z "$MEDIA_FILE" ]; then
  echo "❌ لطفا مسیر فایل بکاپ دیتابیس و مدیا رو بدید"
  echo "مثال: ./restore.sh /var/backups/safarnameh/db_2025-08-31.sql /var/backups/safarnameh/media_2025-08-31.tar.gz"
  exit 1
fi

# 1. ریستور دیتابیس
echo "📦 ریستور دیتابیس..."
cat $DB_FILE | docker exec -i postgres_db psql -U postgres safarname24

# 2. ریستور مدیا
echo "🖼  ریستور مدیا..."
tar -xzf $MEDIA_FILE -C /var/hotelscript-v2

echo "✅ ریستور کامل شد"
