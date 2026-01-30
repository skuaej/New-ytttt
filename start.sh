#!/bin/sh
# ===============================
# Start script for Koyeb deployment
# ===============================

# Optional: check if cookies exist
if [ ! -f ./app/cookies.txt ]; then
    echo "WARNING: cookies.txt not found. Some YouTube videos may fail."
fi

# Run the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
