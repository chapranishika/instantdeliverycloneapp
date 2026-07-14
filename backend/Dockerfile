FROM python:3.11-slim

# System deps for faiss, lightgbm, numpy, asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching — only reruns if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create the data dir — ML artifacts are mounted via Docker volume in local dev
# and are COPY'd in below for production builds where artifacts exist
RUN mkdir -p ./data/processed/models

# Copy pre-built ML artifacts if they exist (won't fail if dir is empty)
COPY data/ ./data/

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Production: 2 workers. For local dev, docker-compose overrides this with --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
