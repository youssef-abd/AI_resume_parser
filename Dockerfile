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

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["bash", "-c", "\
    uvicorn app.main:app --host 0.0.0.0 --port 8000 & \
    streamlit run src/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 \
"]