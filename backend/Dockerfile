# ─────────────────────────────────────────────────────────────────────────────
#  AI Health Companion — Backend Dockerfile
#  Multi-stage build: dependency install → slim runtime image
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools required by some Python packages (e.g. cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into an isolated prefix
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Production runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.12/site-packages"

# Runtime OS dependencies (PyMySQL is pure Python; no native MySQL libs needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy application source
COPY . .

# Persistent volume mount-point for prescription uploads
RUN mkdir -p /app/uploads/prescriptions

VOLUME ["/app/uploads"]

EXPOSE 8000

# Note: Health check is defined in docker-compose.yml (CMD curl -f http://localhost:8000/health)

# Entrypoint: wait for MySQL TCP port, run Alembic migrations, then start uvicorn
CMD ["sh", "-c", "\
  echo 'Waiting for MySQL to be ready...' && \
  until python -c \
    \"import socket, sys; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('mysql', 3306)); s.close(); sys.exit(r)\" \
    2>/dev/null; do \
      echo '  MySQL not ready yet, retrying in 3s...'; sleep 3; \
  done && \
  echo 'MySQL is up — running migrations...' && \
  alembic upgrade head && \
  echo 'Migrations done — starting uvicorn...' && \
  uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-level info"]



