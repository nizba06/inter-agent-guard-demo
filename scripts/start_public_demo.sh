#!/bin/sh
# Start IntelBrief API + Streamlit for single-port public hosting (Render, etc.)
set -e
cd /app

export LLM_BACKEND="${LLM_BACKEND:-scripted}"
export FIXTURE_MODE="${FIXTURE_MODE:-local}"
export REQUIRE_ML_MODEL="${REQUIRE_ML_MODEL:-true}"
export ENABLE_TRUST_ATTESTATION="${ENABLE_TRUST_ATTESTATION:-true}"
export AGENTGUARD_MODE="${AGENTGUARD_MODE:-enforce}"
export ENVIRONMENT="${ENVIRONMENT:-production}"
export API_HOST=127.0.0.1
export API_PORT=8000
export INTELBRIEF_API_URL=http://127.0.0.1:8000/api/v1

PORT="${PORT:-8501}"

# Bind Streamlit on 0.0.0.0:$PORT first so Render's port scan passes quickly.
echo "Starting Streamlit on 0.0.0.0:${PORT}..."
streamlit run ui/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT}" \
  --server.headless=true \
  --browser.gatherUsageStats=false &
STREAMLIT_PID=$!

echo "Starting API on ${API_HOST}:${API_PORT}..."
python -m intelbrief &
API_PID=$!

echo "Waiting for API health (Streamlit is already bound on ${PORT})..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 20 25 30; do
  if curl -sf "http://127.0.0.1:8000/api/v1/health" >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  sleep 2
done

# Keep container alive; exit if either process dies.
while kill -0 "${STREAMLIT_PID}" 2>/dev/null && kill -0 "${API_PID}" 2>/dev/null; do
  sleep 2
done

echo "A process exited (streamlit=${STREAMLIT_PID}, api=${API_PID}); shutting down."
wait || true
exit 1
