#!/bin/bash
set -euo pipefail

PORT="${PORT:-7860}"
export PORT
export PYTHONPATH="/app:${PYTHONPATH:-}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set. Configure it in your Space secrets." >&2
  exit 1
fi

export API_BASE_URL="/api"

# Run database migrations with timeout
>&2 echo "Running Alembic migrations..."
ALEMBIC_CFG=""
if [[ -f "/app/alembic.ini" ]]; then
  ALEMBIC_CFG="/app/alembic.ini"
elif [[ -f "/alembic.ini" ]]; then
  ALEMBIC_CFG="/alembic.ini"
else
  echo "ERROR: alembic.ini not found" >&2
  exit 1
fi
>&2 echo "Using Alembic config: ${ALEMBIC_CFG}"

timeout 120 alembic -c "${ALEMBIC_CFG}" upgrade head || {
  echo "WARNING: Alembic migration timed out or failed, continuing anyway..." >&2
}

# Start FastAPI with more verbose logging
>&2 echo "Starting FastAPI on 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info &
FASTAPI_PID=$!

# Wait a moment and check if FastAPI started
sleep 5
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
  echo "ERROR: FastAPI failed to start" >&2
  exit 1
fi

# Test FastAPI health
if curl -f http://127.0.0.1:8000/health >/dev/null 2>&1; then
  >&2 echo "✅ FastAPI health check passed"
else
  >&2 echo "⚠️ FastAPI health check failed"
fi

# Start Streamlit
>&2 echo "Starting Streamlit on 127.0.0.1:8501"
streamlit run src/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 &
STREAMLIT_PID=$!

# Wait and check Streamlit
sleep 5
if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
  echo "ERROR: Streamlit failed to start" >&2
  exit 1
fi

# Test Streamlit
if curl -f http://127.0.0.1:8501 >/dev/null 2>&1; then
  >&2 echo "✅ Streamlit health check passed"
else
  >&2 echo "⚠️ Streamlit health check failed"
fi

# Start Nginx
>&2 echo "Starting Nginx on port ${PORT}"
mkdir -p /tmp/nginx/client_body_temp /tmp/nginx/proxy_temp /tmp/nginx/fastcgi_temp /tmp/nginx/uwsgi_temp /tmp/nginx/scgi_temp
envsubst '$PORT' < nginx.conf.tmpl > /tmp/nginx.conf

# Show the generated nginx config for debugging
>&2 echo "Generated Nginx config:"
>&2 cat /tmp/nginx.conf

# Test nginx config
nginx -t -c /tmp/nginx.conf || {
  echo "ERROR: Nginx config test failed" >&2
  exit 1
}

>&2 echo "✅ All services started, launching Nginx..."
exec nginx -c /tmp/nginx.conf -g 'daemon off;'