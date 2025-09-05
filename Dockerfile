FROM python:3.13.5-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY src/ ./src/
COPY start.sh ./

RUN pip3 install -r requirements.txt
RUN chmod +x ./start.sh

# Set environment variable for API URL
ENV API_BASE_URL=http://localhost:8000

EXPOSE 8000 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["./start.sh"]