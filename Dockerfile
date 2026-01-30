# =========================
# Base image
# =========================
FROM python:3.10-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# =========================
# Install system dependencies
# =========================
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (yt-dlp JS extraction)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node -v \
    && npm -v

# Set working directory
WORKDIR /app

# Copy Python dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Start the app
CMD ["./start.sh"]
