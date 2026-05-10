# vibe proving Docker image
# Based on Python 3.11 slim for a smaller image and faster startup.

FROM python:3.11-slim

# Working directory
WORKDIR /app

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ .

# Create default config. Docker Compose normally overrides it with ./app/config.toml.
RUN if [ ! -f config.toml ]; then cp config.example.toml config.toml; fi

# Port
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start command
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]
