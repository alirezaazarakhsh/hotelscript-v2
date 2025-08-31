#!/bin/bash

PROJECT_DIR="/var/hotelscript-v2"
BOT_DIR="$PROJECT_DIR/hotel_bot"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"
BOT_LOG="$LOG_DIR/bot.log"

# اجرای دستورات Django
cd $PROJECT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای makemigrations" | tee -a $DJANGO_LOG
python manage.py makemigrations >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای migrate" | tee -a $DJANGO_LOG
python manage.py migrate >> $DJANGO_LOG 2>&1

# اجرای Django با حلقه امن
run_django() {
    while true; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django" | tee -a $DJANGO_LOG
        python manage.py runserver 0.0.0.0:8000 >> $DJANGO_LOG 2>&1
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] سرور Django کرش کرد، دوباره اجرا می‌کنیم..." | tee -a $DJANGO_LOG
        sleep 5
    done
}

# اجرای ربات
run_bot() {
    cd $BOT_DIR
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای ربات" | tee -a $BOT_LOG
    python3 bot.py >> $BOT_LOG 2>&1
}

# اجرای همزمان با & برای پس‌زمینه
run_bot &
run_django
