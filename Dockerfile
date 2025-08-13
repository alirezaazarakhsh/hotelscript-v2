FROM python:3.10-bullseye

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# آپدیت کلیدها و گواهی‌ها قبل از apt-get update
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates gnupg && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["sh", "-c", "exec ./start.sh"]
