import os
import sys
from django.apps import AppConfig


class ReservationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservation'

    def ready(self):
        try:
            import reservation.signals  # noqa: F401
        except Exception:
            pass

        # جلوگیری از اجرا در دستورات migrate و...
        ignored_commands = ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser', 'check']
        if any(cmd in sys.argv for cmd in ignored_commands):
            return

        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        # شروع آپدیت هوشمند و خودکار اسنپ
        try:
            from .snapptrip_service import start_snapp_auto_sync_thread
            start_snapp_auto_sync_thread()
        except Exception:
            pass