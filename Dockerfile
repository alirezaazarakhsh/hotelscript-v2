# Use the official Python 3.10 (bookworm) image to avoid outdated GPG keys
FROM python:3.10-bookworm

# Set the working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (update GPG keys if needed)
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
    gnupg \
    default-libmysqlclient-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Copy start.sh and give execute permissions
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Start the application
CMD ["sh", "-c", "exec ./start.sh"]
