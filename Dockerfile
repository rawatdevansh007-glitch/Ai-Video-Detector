# ==============================================================================
# VeritasVideo - Production Dockerfile for Hugging Face Spaces & Cloud Deployment
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/backend" \
    PORT=7860

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
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files into container
COPY . /app

# Pre-generate calibration sample videos so dashboard sample buttons work immediately
RUN python create_samples.py

# Create non-root user (UID 1000) for Hugging Face Spaces security compatibility
# and ensure all cache/uploads/models directories have full read-write permissions
RUN useradd -m -u 1000 user && \
    mkdir -p /app/cache/uploads /app/samples /app/backend/models /app/dataset/real /app/dataset/ai && \
    chown -R user:user /app && \
    chmod -R 777 /app

USER user

# Expose standard Hugging Face Spaces port (7860)
EXPOSE 7860

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch production server binding to dynamic $PORT (default 7860 on Hugging Face, 10000 on Render)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
