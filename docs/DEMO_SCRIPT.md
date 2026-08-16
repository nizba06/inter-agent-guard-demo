# IntelBrief — 5-minute public demo script

**Title:** IntelBrief — multi-agent pipeline secured by AgentGuard

Use this script for a live demo, Loom/YouTube recording, or conference talk.

---

## Before you start (2 min)

**Hosted (zero setup):** Open the public demo URL from the README.

**Local:**
```powershell
py -3.12 -m pip install -e ".[dev]"
py -3.12 install_model.py
py -3.12 -m intelbrief          # Terminal 1
streamlit run ui/streamlit_app.py   # Terminal 2
```

Open http://localhost:8501 — confirm health row shows **API ok**, **ML model loaded**.

---

## Minute 0:00 — Problem (30 sec)

> "Multi-agent systems pass messages and tool output between agents. If a web page or a forged message poisons one hop, downstream agents can exfiltrate data. AgentGuard inspects every hop with five layers — not just keyword filters."

Point at architecture in README or sidebar info box.

---

## Minute 0:30 — Injection unsecured (45 sec)

1. Leave **Simulate compromised web source** checked.
2. Click **Compare both (injection demo)**.
3. Wait for both runs (~30–60 sec hosted scripted mode; longer with Ollama).

> "Without AgentGuard, the writer follows the hidden instruction: `publish_external`. Attack succeeded."

Open **Run history** → unsecured run → **Run detail** → show `writer_action`.

---

## Minute 1:15 — Injection secured + audit (90 sec)

Select the **secured** run from the same compare.

> "Same brief, same poisoned page — but AgentGuard blocked it."

Open **Run detail**:
- **Blocked at:** (e.g. MCP tool output — Layer 2 — ML scorer)
- **Reason:** `mcp_output: risk=1.000`

Switch to **Audit log**:
- Point at red **Attack blocked** banner
- Read `sender_id: tool:fetch_url_raw` → blocked at **fetch**, before researcher handoff

> "Our novel poisoned page avoids all 57 rule-filter phrases. ML still scored it at risk 1.0."

Show [EVAL_REPORT.md](EVAL_REPORT.md) if audience wants numbers.

---

## Minute 2:45 — Impersonation (60 sec)

1. Click **Impersonation — WITHOUT AgentGuard** → attack succeeds.
2. Click **Impersonation — WITH AgentGuard** → blocked.

Open secured impersonation run → Audit:

> "Different attack: no web fetch. A node sends an unsigned message claiming to be the orchestrator. Blocked at Layer 4 — Trust verifier."

---

## Minute 3:45 — Five layers (45 sec)

| Layer | This demo |
|-------|-----------|
| 1 Rule filter | Old phrase-based attacks |
| 2 ML scorer | Novel fixture / MCP fetch |
| 3 Consistency | Handoff drifts from brief |
| 4 Trust | Impersonation scenario |
| 5 Capability | YAML manifests |

> "Not every layer fires every time — that's defense in depth."

---

## Minute 4:30 — Close (30 sec)

> "IntelBrief is an open demo product. AgentGuard is on PyPI. Clone the repo, or use the hosted demo link. Audit logs give you tamper-evident evidence of what was blocked and where."

**Links to show:**
- Demo repo README
- [EVAL_REPORT.md](EVAL_REPORT.md) — eval evidence
- AgentGuard PyPI / GitHub

---

## Recording tips

| Tip | Why |
|-----|-----|
| Use **hosted demo** or `LLM_BACKEND=scripted` | Predictable outcomes |
| Pre-run Compare both before recording | Warm caches / avoid cold start on Render |
| Zoom browser to 125% | Audience reads audit fields |
| Keep Audit tab visible for 10+ seconds | Viewers need time to read `failure_reason` |

---

## Fallback if live demo fails

1. Open a **pre-recorded run** from Run history.
2. Walk through Audit JSON from a known good secured run.
3. Show [EVAL_REPORT.md](EVAL_REPORT.md) table screenshot.
