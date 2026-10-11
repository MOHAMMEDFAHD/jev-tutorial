# Production-style image for the Jev support decision engine.
# Build:  docker build -t practical-jev-ai .
# Run:    docker run --rm -p 8000:8000 --env-file .env -v jevdata:/data practical-jev-ai
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/tickets.db

WORKDIR /app

# Dependencies first so this layer is cached when only source code changes.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install .

# Run as an unprivileged user; /data holds the SQLite file (mount a volume there).
RUN useradd --create-home --uid 10001 appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# One worker: SQLite is a single-file database. Use Postgres before scaling out workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
