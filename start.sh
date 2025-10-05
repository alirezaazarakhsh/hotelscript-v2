#!/bin/bash

# مسیرهای پروژه
PROJECT_DIR="/app"
LOG_DIR="$PROJECT_DIR/logs"

# ساخت پوشه لاگ‌ها اگر وجود نداشته باشد
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"

# ================= اجرای Django =================
cd $PROJECT_DIR || exit
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" >> $DJANGO_LOG 2>&1
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1
python manage.py makemigrations >> $DJANGO_LOG 2>&1
python manage.py migrate >> $DJANGO_LOG 2>&1

# ================= اجرای سرور Daphne برای ASGI =================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Daphne" >> $DJANGO_LOG 2>&1
exec daphne -b 0.0.0.0 -p 8000 safarnameh24.asgi:application >> $DJANGO_LOG 2>&1