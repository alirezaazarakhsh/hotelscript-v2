# استفاده از ایمیج پایدار پایتون 3.11 مبتنی بر دبیان ۱۲ (bookworm)
FROM python:3.11-slim-bookworm

# تنظیم دایرکتوری کاری
WORKDIR /app

# متغیرهای محیطی
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ۱. رفع تایم‌اوت با فورس کردن IPv4
# ۲. تغییر میرور دبیان به سرور سریع و بدون قطعی
# ۳. نصب ابزارهای مورد نیاز
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    (sed -i 's/deb.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true) && \
    (sed -i 's/deb.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list 2>/dev/null || true) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    tar \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل وابستگی‌ها و نصب پکیج‌ها با میرور پرسرعت و بدون تایم‌اوت
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# کپی کل فایل‌های پروژه
COPY . /app/

# حذف کاراکترهای مخفی ویندوز (\r) از اسکریپت‌ها و اعطای دسترسی اجرایی
RUN (sed -i 's/\r$//' /app/start.sh /app/backup.sh 2>/dev/null || true) && \
    chmod +x /app/start.sh /app/backup.sh

# دستور پیش‌فرض برای اجرای کانتینر
CMD ["bash", "/app/start.sh"]