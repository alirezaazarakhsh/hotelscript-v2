import os
from datetime import datetime
from config import MAX_BACKUPS

class FileManager:
    @staticmethod
    def cleanup_old_backups(backup_dir):
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        files = sorted(os.listdir(backup_dir))
        zip_files = [f for f in files if f.endswith(".zip") or f.endswith(".tar.gz") or f.endswith(".sql")]
        while len(zip_files) > MAX_BACKUPS:
            oldest = zip_files.pop(0)
            os.remove(os.path.join(backup_dir, oldest))

    @staticmethod
    def latest_file(backup_dir, extension=None):
        files = [f for f in os.listdir(backup_dir) if (extension is None or f.endswith(extension))]
        return sorted(files, reverse=True)[0] if files else None

    @staticmethod
    def get_file_datetime(filename):
        try:
            date_part = filename.split('_')[1] + '_' + filename.split('_')[2].split('.')[0]
            return datetime.strptime(date_part, "%Y-%m-%d_%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "نامشخص"