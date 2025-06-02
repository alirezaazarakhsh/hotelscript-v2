import os
import subprocess
from django.conf import settings
from datetime import datetime
import psycopg2

def get_db_config():
    db = settings.DATABASES['default']
    return {
        'ENGINE': db['ENGINE'],
        'NAME': db['NAME'],
        'USER': db['USER'],
        'PASSWORD': db['PASSWORD'],
        'HOST': db['HOST'],
        'PORT': db['PORT'],
    }

def backup_full_db(output_dir=None):
    output_dir = output_dir or os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f'full_backup_{timestamp}.dump')

    config = get_db_config()
    command = [
        'pg_dump',
        '-h', config['HOST'],
        '-p', str(config['PORT']),
        '-U', config['USER'],
        '-F', 'c',
        '-f', backup_file,
        config['NAME'],
    ]
    env = os.environ.copy()
    env['PGPASSWORD'] = config['PASSWORD']

    try:
        subprocess.run(command, check=True, env=env)
        return backup_file
    except subprocess.CalledProcessError as e:
        print("Error during full backup:", e)
        return None

def get_tables_for_app(app_name, config):
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
        query = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE %s;
        """
        like_pattern = f"{app_name}_%"
        cursor.execute(query, (like_pattern,))
        results = cursor.fetchall()
        tables = [r[0] for r in results]
    except Exception as e:
        print("Error fetching tables for app:", e)
    finally:
        if conn:
            conn.close()
    return tables

def backup_app(app_name, output_dir=None):
    output_dir = output_dir or os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f'{app_name}_backup_{timestamp}.dump')

    config = get_db_config()
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
        command.extend(['-t', table])

    env = os.environ.copy()
    env['PGPASSWORD'] = config['PASSWORD']

    try:
        subprocess.run(command, check=True, env=env)
        return backup_file
    except subprocess.CalledProcessError as e:
        print("Error during app backup:", e)
        return None

def restore_backup(backup_file):
    if not os.path.exists(backup_file):
        print("Backup file does not exist:", backup_file)
        return False

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






