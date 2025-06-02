import os
import subprocess
from django.conf import settings
from datetime import datetime

def get_db_config():
    """
    گرفتن تنظیمات دیتابیس از تنظیمات جنگو (یا .env)
    """
    db = settings.DATABASES['default']
    return {
        'ENGINE': db['ENGINE'],
        'NAME': db['NAME'],
        'USER': db['USER'],
        'PASSWORD': db['PASSWORD'],
        'HOST': db['HOST'],
        'PORT': db['PORT'],
    }

def backup_full_db(output_dir='backups'):
    """
    بکاپ کامل از کل دیتابیس PostgreSQL
    """
    config = get_db_config()
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f'full_backup_{timestamp}.sql')

    command = [
        'pg_dump',
        '-h', config['HOST'],
        '-p', str(config['PORT']),
        '-U', config['USER'],
        '-F', 'c',  # فرمت custom (فشرده)
        '-f', backup_file,
        config['NAME'],
    ]

    # محیط متغیرها برای پسورد
    env = os.environ.copy()
    env['PGPASSWORD'] = config['PASSWORD']

    try:
        subprocess.run(command, check=True, env=env)
        return backup_file
    except subprocess.CalledProcessError as e:
        print("Error during full backup:", e)
        return None


def backup_app(app_name, output_dir='backups'):
    """
    بکاپ فقط از جداول مربوط به یک اپلیکیشن (فرض: نام جدول‌ها با app شروع می‌شود)
    برای PostgreSQL باید جدول‌ها رو از DB استخراج کنیم و با pg_dump انتخابی بکاپ بگیریم.
    """
    config = get_db_config()
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f'{app_name}_backup_{timestamp}.sql')

    # این بخش فرضی است، باید جداول اپ را از دیتابیس استخراج کنید
    # مثال: جداول با نام app_name_%
    tables = get_tables_for_app(app_name, config)

    if not tables:
        print(f"No tables found for app {app_name}")
        return None

    command = [
        'pg_dump',
        '-h', config['HOST'],
        '-p', str(config['PORT']),
        '-U', config['USER'],
        '-F', 'c',
        '-f', backup_file,
        config['NAME'],
    ]

    for table in tables:
        command.append('-t')
        command.append(table)

    env = os.environ.copy()
    env['PGPASSWORD'] = config['PASSWORD']

    try:
        subprocess.run(command, check=True, env=env)
        return backup_file
    except subprocess.CalledProcessError as e:
        print("Error during app backup:", e)
        return None

def get_tables_for_app(app_name, config):
    """
    استخراج لیست جداول مربوط به یک اپ از دیتابیس PostgreSQL
    با اتصال psycopg2 و query روی information_schema
    """
    import psycopg2

    conn = None
    tables = []
    try:
        conn = psycopg2.connect(
            dbname=config['NAME'],
            user=config['USER'],
            password=config['PASSWORD'],
            host=config['HOST'],
            port=config['PORT'],
        )
        cursor = conn.cursor()
        query = f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE '{app_name}_%';
        """
        cursor.execute(query)
        results = cursor.fetchall()
        tables = [r[0] for r in results]
    except Exception as e:
        print("Error fetching tables for app:", e)
    finally:
        if conn:
            conn.close()
    return tables

def restore_backup(backup_file):
    """
    ری‌استور بکاپ PostgreSQL با استفاده از pg_restore
    """
    config = get_db_config()

    command = [
        'pg_restore',
        '-h', config['HOST'],
        '-p', str(config['PORT']),
        '-U', config['USER'],
        '-d', config['NAME'],
        '-c',  
        backup_file
    ]

    env = os.environ.copy()
    env['PGPASSWORD'] = config['PASSWORD']

    try:
        subprocess.run(command, check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print("Error during restore:", e)
        return False
