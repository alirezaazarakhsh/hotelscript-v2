#!/bin/bash

# مسیر پوشه بکاپ
BACKUP_DIR=/var/backups/sf24_9xkLp7
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# 1. بکاپ دیتابیس
echo "📦 در حال بکاپ گرفتن از دیتابیس..."
docker exec postgres_db pg_dump -U postgres safarname24 > $BACKUP_DIR/db_$DATE.sql

# 2. بکاپ مدیا
echo "🖼 در حال بکاپ گرفتن از مدیا..."
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /var/hotelscript-v2 media

echo "✅ بکاپ کامل شد: $BACKUP_DIR"
