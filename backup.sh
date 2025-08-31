#!/bin/bash

# مسیر پوشه بکاپ
BACKUP_DIR=/var/backups/sf24_9xkLp7
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# ایجاد پوشه بکاپ اگر وجود نداشته باشد
mkdir -p $BACKUP_DIR
if [ ! -d "$BACKUP_DIR" ]; then
  echo "❌ نمی‌توان پوشه $BACKUP_DIR را ایجاد کرد"
  exit 1
fi

# بررسی دسترسی نوشتن
if [ ! -w "$BACKUP_DIR" ]; then
  echo "❌ دسترسی نوشتن به $BACKUP_DIR وجود ندارد"
  exit 1
fi

# 1. بکاپ دیتابیس
echo "📦 در حال بکاپ گرفتن از دیتابیس..."
if ! docker exec postgres_db pg_dump -U postgres safarname24 > $BACKUP_DIR/db_$DATE.sql 2>/tmp/backup_db_error.log; then
  echo "❌ خطا در بکاپ دیتابیس: $(cat /tmp/backup_db_error.log)"
  exit 1
fi

# 2. بکاپ مدیا
echo "🖼 در حال بکاپ گرفتن از مدیا..."
if [ ! -d "/var/hotelscript-v2/media" ]; then
  echo "❌ پوشه /var/hotelscript-v2/media وجود ندارد"
  exit 1
fi
if ! tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /var/hotelscript-v2 media 2>/tmp/backup_media_error.log; then
  echo "❌ خطا در بکاپ مدیا: $(cat /tmp/backup_media_error.log)"
  exit 1
fi

echo "✅ بکاپ کامل شد: $BACKUP_DIR"
ls -l $BACKUP_DIR