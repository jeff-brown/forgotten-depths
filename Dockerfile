# Multi-stage build for Forgotten Depths MUD
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN groupadd -r mudapp && useradd -r -g mudapp mudapp

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements/base.txt requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application code
COPY src/ src/
COPY scripts/ scripts/
COPY config/ config/
COPY data/ data/
COPY main.py .

# Create necessary directories
RUN mkdir -p logs data/world/rooms && \
    chown -R mudapp:mudapp /app

# Switch to non-root user
USER mudapp

# Expose ports
# 4000 - Telnet server
# 8080 - Web client
EXPOSE 4000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', 4000)); s.close()" || exit 1

# Run the application
CMD ["python", "main.py"]
