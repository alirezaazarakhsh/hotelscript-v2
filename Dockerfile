FROM python:3.10-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Fix GPG keys issue before apt-get update
RUN apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /etc/apt/keyrings && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends gnupg ca-certificates && \
    apt-key del 0xA1B2C3D4E5F6 || true && \
    apt-get update --allow-releaseinfo-change && \
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
