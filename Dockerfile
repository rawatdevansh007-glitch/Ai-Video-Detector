# ==============================================================================
# VeritasVideo - Production Dockerfile for Render Cloud Deployment
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Install required system dependencies (FFmpeg for video transcoding, GL/glib for vision codecs, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files into container
COPY . /app

# Ensure runtime directories exist
RUN mkdir -p /app/cache/uploads /app/samples /app/backend/models /app/dataset/real /app/dataset/ai

# Pre-generate calibration sample videos so dashboard sample buttons work immediately
RUN python create_samples.py

# Expose Render standard port
EXPOSE 10000

# Health check configuration for Render container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch production server binding to dynamic Render $PORT
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
