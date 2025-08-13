python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
python manage.py sync_media_files
python manage.py runserver 0.0.0.0:8000