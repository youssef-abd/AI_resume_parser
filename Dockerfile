FROM python:3.13.5-slim

WORKDIR /app

# Install system dependencies including PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    postgresql-client \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*
RUN cat /etc/nginx/mime.types

# Create necessary directories with proper permissions
RUN mkdir -p /.streamlit && \
    chmod 777 /.streamlit && \
    mkdir -p /.cache && \
    chmod 777 /.cache

COPY requirements.txt ./
COPY alembic.ini ./
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY src/ ./src/
COPY start.sh ./
COPY nginx.conf.tmpl ./

RUN pip3 install -r requirements.txt
# Preload spaCy model (best-effort) and sentence-transformers to reduce cold start
RUN python -m spacy download en_core_web_sm || true
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN chmod +x ./start.sh

# Set environment variables
ENV HOST="0.0.0.0"
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 CMD bash -lc "curl -fsS http://127.0.0.1:${PORT:-7860}/api/healthz || exit 1"

ENTRYPOINT ["./start.sh"]