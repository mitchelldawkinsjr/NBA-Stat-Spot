FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl and supercronic
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L -o /usr/local/bin/supercronic https://github.com/aptible/supercronic/releases/download/v0.2.26/supercronic-linux-amd64 && \
    chmod +x /usr/local/bin/supercronic && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY backend /app

# Copy crontab file
COPY backend/crontab /app/crontab

# Expose port
EXPOSE 8000

# Set PORT environment variable explicitly
ENV PORT=8000

# Default command (can be overridden by fly.toml processes)
# Start uvicorn server - must listen on 0.0.0.0 for Fly.io
# Use shell form to allow env var substitution
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

