# ArcHillx v1.0.0 — Dockerfile
# Build:  docker build -t archillx .
# Run (SQLite):  docker run -p 8000:8000 --env-file .env -v archillx_data:/app/data archillx
# Run (MySQL):   docker run -p 8000:8000 --env-file .env -e DB_TYPE=mysql archillx

FROM python:3.12-slim

# System dependencies
# - default-libmysqlclient-dev: required by PyMySQL C extension (optional, pure-Python fallback exists)
# - curl: health check
# - unixodbc-dev: required when DB_TYPE=mssql (pyodbc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -u 1000 archillx
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data and evidence directories and set ownership
RUN mkdir -p /app/data /app/evidence && chown -R archillx:archillx /app

USER archillx

# Environment defaults (override via --env-file or -e flags)
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DB_TYPE=sqlite \
    DB_NAME=archillx \
    DATABASE_URL=sqlite:////app/data/archillx.db \
    SKILLS_DIR=/app/app/skills \
    EVIDENCE_DIR=/app/evidence \
    ROUTING_RULES_PATH=/app/configs/routing_rules.yaml \
    LOG_LEVEL=INFO

EXPOSE 8000

# Persistent storage volume for SQLite file and evidence logs
VOLUME ["/app/data", "/app/evidence"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
