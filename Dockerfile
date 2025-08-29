FROM python:3.13-slim

LABEL org.opencontainers.image.title="api-server-template"
#LABEL org.opencontainers.image.version="latest"

WORKDIR /app

# Copy the source code and configuration files
COPY src /app/src
COPY migrations /app/migrations
COPY pyproject.toml setup.py alembic.ini ./

# Install uv and use it to install dependencies
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache-dir -e .

# Expose port (default to 8080 if PORT is not set)
EXPOSE 8080

# Set environment variables
ENV API_SERVER_HOST=0.0.0.0
ENV API_SERVER_LOG_LEVEL=INFO
#
# The '-- ENV VAR_NAME{!}' is pocessed by docker-run.sh script
# Required for database connection
# -- ENV API_SERVER_DATABASE_URL!

# Run the application
CMD ["api-server", "--host=0.0.0.0", "--port=8080", "--no-reload"]