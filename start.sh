#!/bin/bash

PROJECT_DIR="/var/hotelscript-v2"
BOT_DIR="$PROJECT_DIR/hotel_bot"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p $LOG_DIR

DJANGO_LOG="$LOG_DIR/django.log"
BOT_LOG="$LOG_DIR/bot.log"

# فعال کردن virtualenv اگر دارید
# source $PROJECT_DIR/venv/bin/activate

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای collectstatic" | tee -a $DJANGO_LOG
python manage.py collectstatic --noinput >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای makemigrations" | tee -a $DJANGO_LOG
python manage.py makemigrations >> $DJANGO_LOG 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای migrate" | tee -a $DJANGO_LOG
python manage.py migrate >> $DJANGO_LOG 2>&1

# اجرای ربات در پس‌زمینه بدون حلقه بی‌پایان
cd $BOT_DIR
echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای ربات" | tee -a $BOT_LOG
python3 bot.py >> $BOT_LOG 2>&1 &

# اجرای Django با حلقه امن ولی با محدودیت ری‌استارت
cd $PROJECT_DIR
MAX_RESTARTS=5
COUNT=0
while [ $COUNT -lt $MAX_RESTARTS ]; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] اجرای سرور Django" | tee -a $DJANGO_LOG
    python manage.py runserver 0.0.0.0:8000 >> $DJANGO_LOG 2>&1
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] سرور Django با موفقیت متوقف شد." | tee -a $DJANGO_LOG
        break
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] سرور کرش کرد، ری‌استارت ($COUNT/$MAX_RESTARTS) ..." | tee -a $DJANGO_LOG
        COUNT=$((COUNT+1))
        sleep 5
    fi
done

if [ $COUNT -eq $MAX_RESTARTS ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] سرور Django بیش از حد ری‌استارت شد، متوقف می‌کنیم!" | tee -a $DJANGO_LOG
fi
