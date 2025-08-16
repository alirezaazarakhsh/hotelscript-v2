# Use the official Python image
FROM python:3.10

# Set the working directory to /app
WORKDIR /app

# Set environment variables to avoid writing bytecode and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies from requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files to /app directory in the container
COPY . .

# Install system dependencies (e.g., libmysqlclient-dev for MySQL)
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy start.sh file and set executable permissions
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Default command to run start.sh
CMD ["sh", "-c", "exec ./start.sh"]