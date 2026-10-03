# PneumoScan AI API for a Hugging Face Docker Space (CPU).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000.
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY --chown=user app ./app
COPY --chown=user samples ./samples
COPY --chown=user metrics ./metrics
COPY --chown=user weights ./weights

USER user
# Accounts/history live in SQLite. /data is the Space's persistent storage (if enabled);
# without it the database is under /tmp and resets when the Space restarts.
ENV USE_MOCK_MODELS=false \
    DEVICE=cpu \
    COOKIE_SECURE=true \
    HISTORY_ENABLED=true \
    MOCK_LATENCY_MS=0
EXPOSE 7860
CMD ["sh", "-c", "if [ -w /data ]; then DB=/data/history.db; else mkdir -p /tmp/pneumoscan && DB=/tmp/pneumoscan/history.db; fi; DATABASE_URL=sqlite:///$DB exec uvicorn app.main:app --host 0.0.0.0 --port 7860"]
