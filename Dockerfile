FROM python:3.10

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . /app/

# نصب system dependencies
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev curl && \
    rm -rf /var/lib/apt/lists/*

# اجرای start.sh
RUN chmod +x /app/start.sh

CMD ["sh", "-c", "exec ./start.sh"]
