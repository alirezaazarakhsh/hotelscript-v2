FROM python:3.10

# تنظیم مسیر کاری
WORKDIR /app

# جلوگیری از نوشتن فایل‌های pyc و فعال کردن خروجی فوری
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# کپی requirements و نصب آنها
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . /app/

# نصب system dependencies برای Django و ابزارهای مورد نیاز
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev curl docker.io postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# دادن دسترسی اجرایی به اسکریپت‌ها
RUN chmod +x /app/start.sh /app/backup.sh

# دستور پیش‌فرض برای اجرای Django یا بات
CMD ["bash", "/app/start.sh"]
