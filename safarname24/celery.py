import os
from celery import Celery

# تنظیم محیط Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safarname24.settings')

# ایجاد نمونه Celery
app = Celery('safarname24')

# بارگذاری تنظیمات از فایل settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# کشف خودکار وظایف از اپلیکیشن‌های Django
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """تسک دیباگ برای تست اولیه Celery"""
    print(f'Request: {self.request!r}')