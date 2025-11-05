# استفاده از ایمیج پایه پایتون 3.10
FROM python:3.10-slim

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

# به‌روزرسانی pip
RUN pip install --upgrade pip

# کپی requirements و نصب آنها
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . /app/

# دادن دسترسی اجرایی به اسکریپت‌ها
RUN chmod +x /app/start.sh /app/backup.sh

# دستور پیش‌فرض (توسط docker-compose override می‌شود)
CMD ["bash", "/app/start.sh"]