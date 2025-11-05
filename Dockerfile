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
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# به‌روزرسانی pip
RUN pip install --upgrade pip

# ابتدا پکیج‌های مشکل‌ساز را نصب کن
RUN pip install --no-cache-dir typing-extensions==4.8.0
RUN pip install --no-cache-dir urllib3==1.26.18

# کپی requirements و نصب آنها
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . /app/

# دادن دسترسی اجرایی به اسکریپت‌ها
RUN chmod +x /app/start.sh /app/backup.sh

# دستور پیش‌فرض (توسط docker-compose override می‌شود)
CMD ["bash", "/app/start.sh"]