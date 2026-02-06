# Stage 1: Base build stage
FROM python:3.12-slim AS builder

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for caching benefit
RUN pip install --upgrade pip --root-user-action=ignore
COPY requirements.txt /app/
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Ensure postgres driver is available even when lock/export is stale
RUN pip install --no-cache-dir --root-user-action=ignore psycopg2-binary

# --- Stage 2: Production stage ---
FROM python:3.12-slim

# Receive host UID/GID at build time (with defaults)
ARG APP_UID=1000
ARG APP_GID=1000

# Install runtime dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    postgresql-client \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create group/user, create /app, and set ownership (idempotent)
RUN set -eux; \
    groupadd -g "${APP_GID}" -f appuser || true; \
    id -u appuser >/dev/null 2>&1 || useradd -m -u "${APP_UID}" -g "${APP_GID}" appuser; \
    mkdir -p /app; \
    chown -R "${APP_UID}:${APP_GID}" /app

# Set working dir
WORKDIR /app

# Copy deps from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy code (assign ownership at copy time)
COPY --chown=${APP_UID}:${APP_GID} . .

# Use project entrypoint script
COPY --chown=${APP_UID}:${APP_GID} docker-entrypoint.sh /app/entrypoint.sh

# Prepare runtime directories
RUN set -eux; \
    mkdir -p /app/staticfiles /app/media /app/logs /app/backup; \
    chown -R "${APP_UID}:${APP_GID}" /app/staticfiles /app/media /app/logs /app/backup; \
    chmod -R 755 /app/staticfiles /app/media /app/logs /app/backup /app/entrypoint.sh

USER appuser

EXPOSE 8000
CMD ["/app/docker-entrypoint.sh"]
