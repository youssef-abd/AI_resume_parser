#!/bin/bash
set -euo pipefail

PORT="${PORT:-7860}"
export PORT

# Ensure DATABASE_URL is provided (e.g., via Space Secrets)
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set. Configure it in your Space secrets." >&2
  exit 1
fi

# Set API_BASE_URL for the UI to the internal path behind Nginx
export API_BASE_URL="/api"

# Run database migrations (idempotent)
>&2 echo "Running Alembic migrations..."
alembic upgrade head || { echo "Alembic failed" >&2; exit 1; }

# Start FastAPI (internal)
>&2 echo "Starting FastAPI on 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-server-header --no-access-log &

# Start Streamlit (internal)
>&2 echo "Starting Streamlit on 127.0.0.1:8501"
streamlit run src/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 &

# Render Nginx config with PORT and start Nginx in foreground
>&2 echo "Starting Nginx on port ${PORT}"
export PORT
envsubst '$PORT' < nginx.conf.tmpl > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'