FROM python:3.13.5-slim

WORKDIR /app

# Install system dependencies including PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories with proper permissions
RUN mkdir -p /.streamlit && \
    chmod 777 /.streamlit && \
    mkdir -p /.cache && \
    chmod 777 /.cache

COPY requirements.txt ./
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY src/ ./src/
COPY start.sh ./

RUN pip3 install -r requirements.txt
RUN chmod +x ./start.sh

# Set environment variables
ENV DATABASE_URL="postgresql://postgres:postgres@db:5432/resume_parser"
ENV API_BASE_URL=http://localhost:8000

EXPOSE 8000 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["./start.sh"]