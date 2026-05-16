# Wise Team OS - production container
# Builds an image runnable on Railway / Render / Fly / Docker.
#
# Required runtime env vars:
#   ANTHROPIC_API_KEY  - Claude API key
#   DATABASE_URL       - Postgres URL (Railway auto-injects); falls back to SQLite if unset
#   AGNO_TELEMETRY     - set to 'false' (default in main.py)
#   PORT               - port to bind (Railway injects; defaults to 7777)

FROM python:3.12-slim

WORKDIR /app

# Install only what we need
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy source needed at runtime (agno editable install + our app)
COPY libs/agno /app/libs/agno
COPY wiseteam_os /app/wiseteam_os

# Install agno from the local fork + production runtime deps
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/libs/agno \
    && pip install --no-cache-dir -r /app/wiseteam_os/requirements.txt

# Run as non-root
RUN useradd --create-home --shell /bin/bash wiseteam
USER wiseteam

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGNO_TELEMETRY=false

EXPOSE 7777

# Bind to $PORT (Railway) or 7777 (local). uvicorn directly so PORT works.
CMD uvicorn wiseteam_os.main:app --host 0.0.0.0 --port ${PORT:-7777}
