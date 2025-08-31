#!/bin/bash

# مسیر پروژه
PROJECT_DIR="/var/hotelscript-v2"
BOT_DIR="$PROJECT_DIR/hotel_bot"

# مسیر لاگ‌ها
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"
BOT_LOG="$LOG_DIR/bot.log"

# تابع برای اجرای امن با ری‌استارت در صورت کرش
run_forever() {
    CMD=$1
    LOG=$2
    while true; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای: $CMD" | tee -a $LOG
        $CMD >> $LOG 2>&1
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] کرش کرد یا متوقف شد. دوباره اجرا می‌کنیم..." | tee -a $LOG
        sleep 5
    done
}

# اجرای ربات در پس‌زمینه
cd $BOT_DIR
run_forever "python3 bot.py" $BOT_LOG &

# اجرای دستورات Django
cd $PROJECT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای makemigrations" | tee -a $DJANGO_LOG
python manage.py makemigrations >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای migrate" | tee -a $DJANGO_LOG
python manage.py migrate >> $DJANGO_LOG 2>&1

# اجرای سرور Django با ری‌استارت در صورت کرش
run_forever "python manage.py runserver 0.0.0.0:8000" $DJANGO_LOG
