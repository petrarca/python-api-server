# Multi-stage build for api-server
# Stage 1: Build the package
FROM python:3.13 AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv and build dependencies
RUN pip install --no-cache-dir uv

# Copy source files
COPY src/ /app/src/
COPY pyproject.toml /app/

# Build the package
RUN uv pip install --system --no-cache-dir setuptools
RUN uv pip install --system --no-cache-dir --no-build-isolation -e .
RUN pip install --no-cache-dir build
RUN python -m build

# Stage 2: Runtime image
FROM python:3.13-slim

LABEL org.opencontainers.image.title="api-server"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install built package
COPY --from=builder /app/dist /app/dist
RUN pip install --no-cache-dir /app/dist/*.whl

# Copy configuration files
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

EXPOSE 8080

# Set environment variables
ENV API_SERVER_HOST=0.0.0.0
ENV API_SERVER_PORT=8080
ENV API_SERVER_LOG_LEVEL=INFO

# Required environment variables (must be set at runtime):
#   API_SERVER_DATABASE_URL - Database connection URL
#
# Optional environment variables:
#   API_SERVER_LOG_LEVEL - Log level (default: INFO)
#   API_SERVER_PROFILES - Server profiles (rest, graphql)

CMD ["api-server", "run", "--no-reload"]