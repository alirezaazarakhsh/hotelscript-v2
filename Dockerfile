# استفاده از Python 3.10 بر پایه Debian Bullseye (پایدارتر)
FROM python:3.10-bullseye

# مسیر کاری داخل کانتینر
WORKDIR /app

# جلوگیری از تولید pyc و فعال کردن خروجی بدون بافر
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب وابستگی‌های سیستمی
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

# کپی فایل وابستگی‌ها و نصب پکیج‌های پایتون
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# کپی همه فایل‌ها به داخل کانتینر
COPY . .

# کپی و فعال کردن اسکریپت استارت
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# دستور پیش‌فرض اجرا
CMD ["sh", "-c", "exec ./start.sh"]
