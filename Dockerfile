########################
# Stage 1 — Builder
########################
FROM python:3.12-slim AS builder

USER root
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY uv.lock ./uv.lock
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md

# 1. Install dependencies ONLY. This layer caches heavily!
RUN uv sync --no-install-project

# 2. Copy application code
COPY dyresearch ./dyresearch
COPY config.env ./config.env

# 3. Sync again to install the dyresearch project itself
RUN uv sync

########################
# Stage 2 — Runtime
########################
FROM python:3.12-slim

USER root
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# ONLY copy the app code and the virtual environment from the builder
COPY --from=builder /app /app

# Tell uv to use the virtual environment we copied over
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Run using the venv's python environment directly
ENTRYPOINT ["uv", "run", "uvicorn", "dyresearch.app.server:app", "--host", "0.0.0.0", "--port", "8000"]