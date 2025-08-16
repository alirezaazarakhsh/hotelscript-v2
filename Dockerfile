# Use the official Python 3.10 slim image to reduce size
FROM python:3.10-slim

# Set the working directory to /app
WORKDIR /app

# Set environment variables to avoid writing bytecode and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and update GPG keys
RUN apt-get update && \
    apt-get install -y gnupg && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138 0E98404D386FA1D9 112695A0E3C5F4F8 && \
    apt-get update && \
    apt-get install -y --no-install-recommends default-libmysqlclient-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files to /app
COPY . .

# Copy and set executable permissions for start.sh
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Default command to run start.sh
CMD ["sh", "-c", "exec ./start.sh"]