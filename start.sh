#!/bin/bash
set -euo pipefail

PORT="${PORT:-7860}"
export PORT
# Ensure Python can import the local 'app' package for Alembic env.py
export PYTHONPATH="/app:${PYTHONPATH:-}"

# Ensure DATABASE_URL is provided (e.g., via Space Secrets)
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set. Configure it in your Space secrets." >&2
  exit 1
fi

# Set API_BASE_URL for the UI to the internal path behind Nginx
export API_BASE_URL="/api"

# Run database migrations (idempotent)
>&2 echo "Running Alembic migrations..."
# Find Alembic config path dynamically
ALEMBIC_CFG=""
if [[ -f "/app/alembic.ini" ]]; then
  ALEMBIC_CFG="/app/alembic.ini"
elif [[ -f "/alembic.ini" ]]; then
  ALEMBIC_CFG="/alembic.ini"
else
  echo "ERROR: alembic.ini not found in /app or /" >&2
  ls -la / /app || true
  exit 1
fi
>&2 echo "Using Alembic config: ${ALEMBIC_CFG}"

alembic -c "${ALEMBIC_CFG}" upgrade head || { echo "Alembic failed" >&2; exit 1; }

# Start FastAPI (internal)
>&2 echo "Starting FastAPI on 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-server-header --no-access-log &

# Start Streamlit (internal)
>&2 echo "Starting Streamlit on 127.0.0.1:8501"
streamlit run src/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 &

# Render Nginx config with PORT and start Nginx in foreground
>&2 echo "Starting Nginx on port ${PORT}"
export PORT
# Pre-create Nginx temp directories to avoid permission/missing dir errors
mkdir -p /tmp/nginx/client_body_temp /tmp/nginx/proxy_temp /tmp/nginx/fastcgi_temp /tmp/nginx/uwsgi_temp /tmp/nginx/scgi_temp
envsubst '$PORT' < nginx.conf.tmpl > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'