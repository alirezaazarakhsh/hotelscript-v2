#!/bin/bash

DB_FILE=$1
MEDIA_FILE=$2

# ===================== متغیرهای داکر و مسیرها =====================
CONTAINER_NAME="${DB_CONTAINER:-zarvantrip_postgres_db}"
DB_NAME="${DB_NAME:-zarvantrip}"
DB_USER="${DB_USER:-postgres}"
MEDIA_DIR="${MEDIA_DIR:-/var/hotelscript-v2/media}"

if [ "$DB_FILE" = "dummy_db" ] && [ "$MEDIA_FILE" = "dummy_media" ]; then
  echo "❌ حداقل یکی از فایل‌های دیتابیس یا مدیا باید مشخص شود."
  exit 1
fi

# ---------------- ریستور دیتابیس ----------------
if [ "$DB_FILE" != "dummy_db" ]; then
  if [ ! -f "$DB_FILE" ]; then
    echo "❌ فایل دیتابیس $DB_FILE وجود ندارد."
    exit 1
  fi
  echo "📦 در حال ریستور دیتابیس از $DB_FILE در کانتینر $CONTAINER_NAME (دیتابیس $DB_NAME)..."
  if ! docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$DB_FILE" 2>/tmp/restore_db_error.log; then
    echo "❌ خطا در ریستور دیتابیس: $(cat /tmp/restore_db_error.log)"
    exit 1
  fi
  echo "✅ ریستور دیتابیس انجام شد."
fi

# ---------------- ریستور مدیا ----------------
if [ "$MEDIA_FILE" != "dummy_media" ]; then
  if [ ! -f "$MEDIA_FILE" ]; then
    echo "❌ فایل مدیا $MEDIA_FILE وجود ندارد."
    exit 1
  fi
  
  # اطمینان از وجود پوشه مدیا
  mkdir -p "$MEDIA_DIR"
  
  echo "🖼 در حال ریستور مدیا از $MEDIA_FILE به مسیر $MEDIA_DIR..."
  if ! tar -xzf "$MEDIA_FILE" -C "$MEDIA_DIR" 2>/tmp/restore_media_error.log; then
    echo "❌ خطا در ریستور مدیا: $(cat /tmp/restore_media_error.log)"
    exit 1
  fi
  echo "✅ ریستور مدیا انجام شد."
fi

echo "✅ ریستور کامل انجام شد."