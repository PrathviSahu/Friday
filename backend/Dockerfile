# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────
#  F.R.I.D.A.Y. backend image — FastAPI + Groq/Gemini AI brain,
#  STT (Groq Whisper free tier), memory, career OS, etc.
#
#  macOS-only automation (open/close apps, system volume, display
#  lock) is guarded by IS_MAC checks inside the services and
#  degrades gracefully on Linux/Windows — no code changes needed.
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /app

# Minimal system deps. Playwright browser deps are added only when
# INSTALL_BROWSERS=1 (career job scraping) to keep the default image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Playwright Chromium for the career job scraper.
#   docker compose build --build-arg INSTALL_BROWSERS=1
#   (or set INSTALL_BROWSERS=1 in .env)
ARG INSTALL_BROWSERS=0
RUN if [ "$INSTALL_BROWSERS" = "1" ]; then \
        pip install --no-cache-dir playwright && \
        playwright install --with-deps chromium; \
    fi

# App source
COPY . .

# Writable runtime dirs + non-root user
RUN mkdir -p /app/data /app/temp_audio && \
    useradd -m -u 1000 friday && \
    chown -R friday:friday /app

USER friday

EXPOSE 8000

# Single worker: Support dynamic PORT environment variable (Render / Cloud default).
# --no-proxy-headers is REQUIRED (see auth.py / app.py): uvicorn's default
# proxy-headers mode rewrites request.client from client-supplied
# X-Forwarded-For / X-Real-IP, letting a remote attacker spoof 127.0.0.1 and
# bypass owner authentication. Never remove this flag.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-proxy-headers"]
