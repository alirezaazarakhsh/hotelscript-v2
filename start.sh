#!/bin/bash

# مسیر پروژه
PROJECT_DIR="/var/hotelscript-v2"
BOT_DIR="$PROJECT_DIR/hotel_bot"

# اجرای دستورات Django
cd $PROJECT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic"
python manage.py collectstatic --noinput

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای makemigrations"
python manage.py makemigrations

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای migrate"
python manage.py migrate

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django"
python manage.py runserver 0.0.0.0:8000 &   # اجرا در پس‌زمینه

# اجرای ربات
cd $BOT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] بارگذاری فایل .env و اجرای ربات"
export $(grep -v '^#' .env | xargs)   # بارگذاری متغیرهای محیطی
python3 bot.py
