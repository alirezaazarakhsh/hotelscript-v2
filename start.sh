#!/bin/bash

# مسیرهای پروژه
PROJECT_DIR="/app"             # مسیر پروژه در کانتینر (مطابق docker-compose)
BOT_DIR="$PROJECT_DIR/hotel_bot"
LOG_DIR="$PROJECT_DIR/logs"

# ساخت پوشه لاگ‌ها اگر وجود نداشته باشد
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"
BOT_LOG="$LOG_DIR/bot.log"

# ================= اجرای Django =================
cd $PROJECT_DIR || exit
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1
python manage.py makemigrations >> $DJANGO_LOG 2>&1
python manage.py migrate >> $DJANGO_LOG 2>&1

# ================= اجرای ربات =================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] بارگذاری فایل .env و اجرای ربات" | tee -a $BOT_LOG
# بارگذاری متغیرهای محیطی از .env
if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs)
else
    echo "⚠️ فایل .env پیدا نشد!" | tee -a $BOT_LOG
fi

# اجرای ربات در پس‌زمینه
python3 $BOT_DIR/bot.py >> $BOT_LOG 2>&1 &

# ================= اجرای سرور Django =================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django" | tee -a $DJANGO_LOG
python manage.py runserver 0.0.0.0:8000
