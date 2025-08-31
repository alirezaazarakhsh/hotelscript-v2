#!/bin/bash

# مسیرهای پروژه
PROJECT_DIR="/app"             # مسیر پروژه در کانتینر (مطابق docker-compose)
LOG_DIR="$PROJECT_DIR/logs"

# ساخت پوشه لاگ‌ها اگر وجود نداشته باشد
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"

# ================= اجرای Django =================
cd $PROJECT_DIR || exit
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1
python manage.py makemigrations >> $DJANGO_LOG 2>&1
python manage.py migrate >> $DJANGO_LOG 2>&1

# ================= اجرای سرور Django =================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django" | tee -a $DJANGO_LOG
python manage.py runserver 0.0.0.0:8000
