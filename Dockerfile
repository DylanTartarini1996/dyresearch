########################
# Stage 1 — Builder
########################
FROM python:3.12-slim AS builder

USER root


# Install uv (fast dependency manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH" \
    UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /dyresearch

# Copy dependency list and install packages
COPY uv.lock ./uv.lock
COPY pyproject.toml ./pyproject.toml
RUN uv sync

# Copy application code
COPY dyresearch ./dyresearch
COPY agent.py ./agent.py
COPY config.env ./config.env


########################
# Stage 2 — Runtime
########################
FROM python:3.12-slim

USER root


# Install uv (small single binary, no build tools)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set environment vars
ENV PATH="/root/.local/bin:$PATH" \
    UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1

WORKDIR /dyresearch

# Copy installed Python packages and source code from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /dyresearch /dyresearch

# Expose FastAPI port
EXPOSE 8000

ENTRYPOINT ["uv", "run", "adk", "web", "--host", "0.0.0.0", "--port", "8000"]
