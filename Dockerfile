FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for runtime utilities
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn

# Copy Django project
COPY . /app

# Expose Django port
EXPOSE 8000

# Entrypoint handles DB wait, migrations, then start server
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DJANGO_SETTINGS_MODULE=config.settings

CMD ["/entrypoint.sh"]
