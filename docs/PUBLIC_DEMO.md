# Deploy IntelBrief on Render.com

Public **zero-setup** demo URL (scripted LLM + full AgentGuard stack). Visitors use the UI in-browser; they do **not** trigger `pip install` — AgentGuard is baked into the container at build time.

---

## Before you deploy

1. Push **`inter-agent-guard-demo`** to GitHub (public, or private repo connected to Render).
2. Confirm these files exist at the repo root:
   - `render.yaml`
   - `Dockerfile.demo`
   - `scripts/start_public_demo.sh`

**Optional local test** (same image as Render):

```powershell
cd inter-agent-guard-demo
docker build -f Dockerfile.demo -t intelbrief-demo .
docker run --rm -p 8501:8501 -e PORT=8501 intelbrief-demo
```

Open http://localhost:8501 — first start may take 2–5 minutes (ML model download).

---

## Step 1 — Create a Render account

1. Go to **https://render.com**
2. Sign up ( **Sign in with GitHub** is easiest )

---

## Step 2 — Deploy with Blueprint (recommended)

1. Render dashboard → **New +** → **Blueprint**
2. **Connect** your GitHub account if prompted
3. Select repository **`inter-agent-guard-demo`**
4. Render detects **`render.yaml`** and shows service **`intelbrief-demo`**
5. Review settings (free plan is fine) → click **Apply**
6. Wait for deploy (**~5–15 minutes** on first run):
   - Docker build (`pip install` + `install_model.py` ONNX download **once**)
   - Container start → FastAPI + Streamlit on Render’s `$PORT`

---

## Step 3 — Get your public URL

1. Open the **`intelbrief-demo`** service in Render
2. Copy the URL at the top, e.g.:
   ```text
   https://intelbrief-demo.onrender.com
   ```
3. Paste it into **`README.md`** under **Try it now → Hosted demo**

---

## Step 4 — Verify the demo

1. Open your Render URL (if the service was sleeping, wait ~30–60s)
2. Confirm the health row shows **API ok** and **ML model loaded**
3. Click **Compare both (injection demo)**
4. Open **Run detail** on the secured run → **Blocked at** should show a layer
5. Open **Audit log** → confirm `mcp_output` or inter-agent block

---

## Manual deploy (if Blueprint fails)

1. **New +** → **Web Service**
2. Connect repo **`inter-agent-guard-demo`**
3. Set:

   | Field | Value |
   |-------|--------|
   | Runtime | **Docker** |
   | Dockerfile path | **`Dockerfile.demo`** |
   | Plan | Free |
   | Health check path | `/` |

4. Environment variables:

   | Key | Value |
   |-----|--------|
   | `LLM_BACKEND` | `scripted` |
   | `FIXTURE_MODE` | `local` |
   | `REQUIRE_ML_MODEL` | `true` |
   | `ENABLE_TRUST_ATTESTATION` | `true` |
   | `AGENTGUARD_MODE` | `enforce` |
   | `ENVIRONMENT` | `production` |

5. **Create Web Service** → wait until **Live**

---

## Free tier notes

| Behavior | What to expect |
|----------|----------------|
| **Sleep after ~15 min idle** | Next visitor waits ~30–60s to wake |
| **Cold start** | Model is baked into the Docker image; startup verifies hash only (~seconds) |
| **PyPI downloads** | Only at **Docker build**, not per visitor |

Tell users: *“First load after idle may take 1–2 minutes.”*

---

## Troubleshooting

| Problem | Action |
|---------|--------|
| Build fails | Render → **Logs** → check `pip install` errors |
| **`Out of memory (used over 512Mi)`** | Ensure `ENVIRONMENT=production` (disables uvicorn reload). Model must be baked in Docker build (`RUN python install_model.py` in `Dockerfile.demo`). Redeploy after pulling latest. If still OOM, upgrade to Starter (512Mi is tight for FastAPI + Streamlit + ONNX). |
| UI loads, ML model missing | Logs → search for `install_model.py` / GitHub download errors |
| API unreachable | Logs → confirm `python -m intelbrief` started |
| Health check fails | First boot is slow; retry or increase startup timeout in service settings |

---

## After deploy — links to share

```text
Try live:   https://YOUR-SERVICE.onrender.com
Install:    pip install inter-agent-guard
Demo repo:  https://github.com/nizba06/inter-agent-guard-demo
Library:    https://github.com/nizba06/agentguard
Docs:       https://inter-agent-guard.readthedocs.io/
```

---

## Custom domain (optional)

Render → your service → **Settings** → **Custom Domain** → e.g. `demo.yourdomain.com`
