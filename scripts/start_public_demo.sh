#!/bin/sh
# Start IntelBrief API + Streamlit for single-port public hosting (Render, etc.)
set -e
cd /app

echo "Checking AgentGuard ML model (skipped if baked into image)..."
python install_model.py

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

# Keep container alive; exit if either process dies.
while kill -0 "${STREAMLIT_PID}" 2>/dev/null && kill -0 "${API_PID}" 2>/dev/null; do
  sleep 2
done

echo "A process exited (streamlit=${STREAMLIT_PID}, api=${API_PID}); shutting down."
wait || true
exit 1
