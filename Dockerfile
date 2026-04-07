# Dockerfile for Hugging Face Spaces deployment
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies step by step for reliability
RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    pydantic>=2.0.0 \
    uvicorn>=0.24.0 \
    requests>=2.31.0 \
    websockets>=12.0

# Install openenv-core
RUN pip install --no-cache-dir "openenv-core[core]>=0.2.2"

# Copy all environment code
COPY . /app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the server
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
