########################
# Stage 1 — Builder
########################
FROM python:3.12-slim AS builder

USER root

# 1. Install build tools for psycopg2 (gcc and libpq-dev)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 2. Safely grab uv without needing curl
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment vars
ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy dependency list and install packages
COPY uv.lock ./uv.lock
COPY pyproject.toml ./pyproject.toml
RUN uv sync

# Copy application code
COPY dyresearch ./dyresearch
COPY app ./app
COPY config.env ./config.env


########################
# Stage 2 — Runtime
########################
FROM python:3.12-slim

USER root

# 3. Install the Postgres runtime library so psycopg2 can actually connect
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Safely grab uv without needing curl
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment vars
ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed Python packages and source code from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Expose FastAPI port
EXPOSE 8000

ENTRYPOINT ["uv", "run", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]