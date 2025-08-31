#!/bin/bash

# اجرای دستورات Django
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# اجرای ربات در پس‌زمینه
cd hotel_bot
python3 bot.py &

# اجرای سرور Django
cd ..
python manage.py runserver 0.0.0.0:8000
