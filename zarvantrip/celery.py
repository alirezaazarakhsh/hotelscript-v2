import os
from celery import Celery

# تنظیم محیط Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zarvantrip.settings')

# ایجاد نمونه Celery
app = Celery('zarvantrip')

# بارگذاری تنظیمات از فایل settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# کشف خودکار وظایف از اپلیکیشن‌های Django
app.autodiscover_tasks()