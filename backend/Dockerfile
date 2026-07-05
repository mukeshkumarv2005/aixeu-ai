# ── Build stage ──────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Build dependencies and application wheel
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir wheel && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels .

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

# Runtime libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /app/wheels
RUN pip install --no-cache-dir --no-index --find-links=/app/wheels /app/wheels/*.whl && \
    rm -rf /app/wheels

# Copy application code
COPY . .

# Non-root user and directory structure setup
RUN useradd -m -u 1000 aevix && \
    mkdir -p /app/storage && \
    chown -R aevix:aevix /app

USER aevix

EXPOSE 8000

# Health check using python standard library to verify application status
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
