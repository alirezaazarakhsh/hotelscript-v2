# استفاده از ایمیج پایه پایتون 3.8 برای سازگاری با docker-compose
FROM python:3.8-slim

# تنظیم مسیر کاری
WORKDIR /app

# جلوگیری از نوشتن فایل‌های pyc و فعال کردن خروجی فوری
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب ابزارهای مورد نیاز
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    tar \
    curl \
    && rm -rf /var/lib/apt/lists/*

# کپی requirements و نصب آنها
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . /app/

# دادن دسترسی اجرایی به اسکریپت‌ها
RUN chmod +x /app/start.sh /app/backup.sh

# دستور پیش‌فرض برای اجرای Django یا سرویس‌های دیگر
CMD ["bash", "/app/start.sh"]
