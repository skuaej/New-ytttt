FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    pip install --upgrade pip

# Set workdir
WORKDIR /app

# Copy files
COPY api.py .
COPY requirements.txt .
COPY cache.json .   # optional
COPY cookies.txt .  # optional

# Install Python deps
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8080

# Run FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
