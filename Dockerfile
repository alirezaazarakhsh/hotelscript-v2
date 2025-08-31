FROM python:3.10

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب dependencies قبل از mount کردن volume
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# کپی بقیه فایل‌ها
COPY ./hotelscript-v2 /app

# نصب system dependencies
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev curl && \
    rm -rf /var/lib/apt/lists/*

# start.sh
COPY ./hotelscript-v2/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["sh", "-c", "exec ./start.sh"]
