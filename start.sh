#!/bin/bash

PROJECT_DIR="/var/hotelscript-v2"
BOT_DIR="$PROJECT_DIR/hotel_bot"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"
BOT_LOG="$LOG_DIR/bot.log"

# اجرای Django
cd $PROJECT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1
python manage.py makemigrations >> $DJANGO_LOG 2>&1
python manage.py migrate >> $DJANGO_LOG 2>&1

# اجرای ربات در پس‌زمینه
echo "[$(date '+%Y-%m-%d %H:%M:%S')] بارگذاری فایل .env و اجرای ربات" | tee -a $BOT_LOG
export $(grep -v '^#' $BOT_DIR/.env | xargs)
python3 $BOT_DIR/bot.py >> $BOT_LOG 2>&1 &

# اجرای سرور Django در جلوی کانتینر (مانع خروج کانتینر می‌شود)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django" | tee -a $DJANGO_LOG
python manage.py runserver 0.0.0.0:8000
