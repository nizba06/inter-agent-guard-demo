#!/bin/sh
# Start IntelBrief API + Streamlit for single-port public hosting (Render, etc.)
set -e
cd /app

echo "Installing AgentGuard ML model (first start may take 1–2 min)…"
python install_model.py

export LLM_BACKEND="${LLM_BACKEND:-scripted}"
export FIXTURE_MODE="${FIXTURE_MODE:-local}"
export REQUIRE_ML_MODEL="${REQUIRE_ML_MODEL:-true}"
export ENABLE_TRUST_ATTESTATION="${ENABLE_TRUST_ATTESTATION:-true}"
export AGENTGUARD_MODE="${AGENTGUARD_MODE:-enforce}"
export API_HOST=127.0.0.1
export API_PORT=8000
export INTELBRIEF_API_URL=http://127.0.0.1:8000/api/v1

echo "Starting API on ${API_HOST}:${API_PORT}…"
python -m intelbrief &
API_PID=$!

for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -sf "http://127.0.0.1:8000/api/v1/health" >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  sleep 2
done

PORT="${PORT:-8501}"
echo "Starting Streamlit on 0.0.0.0:${PORT}…"
exec streamlit run ui/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT}" \
  --server.headless=true \
  --browser.gatherUsageStats=false
