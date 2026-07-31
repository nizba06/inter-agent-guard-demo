# inter-agent-guard — PyPI validation + production-style demo

Standalone project that installs **`inter-agent-guard`** from PyPI (not a local clone) and validates the library with the ONNX ML model **and** a multi-agent LangGraph pipeline that simulates a production failure mode.

| PyPI install name | Python import |
|-------------------|---------------|
| `inter-agent-guard` | `agentguard` |

## What it demonstrates

1. **API smoke tests** — manifests, `inspect_message`, capabilities, MCP wrap  
2. **Production-style pipeline** — `orchestrator → researcher → writer` agents, each driven by an agent model:
   - **Unsecured:** poisoned research handoff reaches the writer (`publish_external…`)
   - **Secured:** `guard.wrap(langgraph)` blocks the injection before the writer acts

Agent models default to **deterministic scripts** (no API keys). For a **real local LLM**, use **Ollama + Llama** (see below). OpenAI is also supported.

## Setup

```powershell
cd inter-agent-guard-demo

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -e .
```

On macOS/Linux, use `python3.12`, `source .venv/bin/activate`, and the same `pip install -e .` command.

### Install ML model (required for enforce-mode)

Downloads `risk_scorer.onnx` + `model.sha256` from the public **v1.0.0** GitHub
release (ONNX assets; package version is 1.1.x) into the installed package
`models/` directory and verifies the SHA-256:

```powershell
py -3.12 install_model.py
# re-download: py -3.12 install_model.py --force
```

`install_model.py` uses public HTTPS first, then falls back to `gh release download` / `GH_TOKEN` if needed.

## Run

### Default (scripted agents — no LLM)

Fast, reproducible, no GPU or API keys. Researcher and writer use fixed Python stubs.

```powershell
py -3.12 run_prod_demo.py
# or full suite (API checks + prod pipeline):
py -3.12 run_validation.py
```

### Real local LLM with Ollama + Llama (recommended)

This runs the **same multi-agent pipeline** (`orchestrator → researcher → writer`) but
**researcher and writer call a real chat model** via [Ollama](https://ollama.com). Default
model: **`llama3.2`**. AgentGuard still uses its own ONNX risk scorer separately.

**Two models in play:**

| Role | Model | Purpose |
|------|--------|---------|
| **Agent LLM** | Ollama `llama3.2` (or your choice) | Generates agent replies in the pipeline |
| **AgentGuard scorer** | `risk_scorer.onnx` (DeBERTa) | Scores inter-agent messages for injection |

#### 1. Install and start Ollama

Download Ollama from https://ollama.com, then in a terminal:

```powershell
# Pull the default demo model (once)
ollama pull llama3.2

# Confirm Ollama is serving (usually auto-starts after install)
ollama list
```

Use another local model if you prefer:

```powershell
ollama pull llama3.1
py -3.12 run_prod_demo.py --llm ollama --model llama3.1
```

#### 2. Install demo + ONNX (if not done already)

```powershell
cd inter-agent-guard-demo
.\.venv\Scripts\Activate.ps1
py -3.12 -m pip install -e .
py -3.12 install_model.py
```

#### 3. Run the production demo with Llama

```powershell
py -3.12 run_prod_demo.py --llm ollama
```

Equivalent using environment variables:

```powershell
$env:DEMO_LLM = "ollama"
$env:DEMO_LLM_MODEL = "llama3.2"   # optional; llama3.2 is the default
py -3.12 run_prod_demo.py
```

On bash:

```bash
export DEMO_LLM=ollama
export DEMO_LLM_MODEL=llama3.2
python3.12 run_prod_demo.py --llm ollama
```

#### 4. What you should see

1. **Unsecured run** — Llama researcher relays poisoned tool text; writer outputs
   `publish_external all confidential pricing data` → attack succeeds.
2. **Secured run** — `guard.wrap()` blocks at `researcher → writer` (often
   `rule_filter: ignore previous instructions`).

First Ollama call may take ~20s while the model loads; later hops are faster.

#### Troubleshooting (Ollama)

| Issue | Fix |
|-------|-----|
| Connection refused to `127.0.0.1:11434` | Start Ollama app or run `ollama serve` |
| Model not found | `ollama pull llama3.2` |
| Writer does not follow injection | Real LLMs sometimes refuse; re-run or use default scripted demo |
| `ResourceTracker` traceback at exit | Harmless Windows/Python 3.12 cleanup noise; demo still passed |

Optional: reduce embedding warnings on exit:

```powershell
$env:TOKENIZERS_PARALLELISM = "false"
py -3.12 run_prod_demo.py --llm ollama
```

### OpenAI (cloud LLM)

```powershell
py -3.12 -m pip install -e ".[openai]"
$env:OPENAI_API_KEY = "sk-..."
py -3.12 run_prod_demo.py --llm openai --model gpt-4o-mini
```

Real LLMs can refuse injections; the **scripted backend** is the reproducible CI path.
AgentGuard still inspects whatever text the model actually emits between agents.

### Other scripts

Novel paraphrase probe (rules + ML + consistency):

```powershell
py -3.12 test_novel_messages.py
```

AgentGuard CLI:

```powershell
py -3.12 -m agentguard status
py -3.12 -m agentguard inspect -m "Summarise public pricing from filings."
```

## Checks in `run_validation.py`

1. Import `agentguard` + version  
2. ONNX install + hash verify + ML scorer loaded  
3. Load YAML manifests (JSON Schema from bundled package)  
4. Block prompt injection via `inspect_message()`  
5. Forward benign inter-agent messages  
6. Capability enforcement (`publish_external` denied)  
7. MCP tool output poisoning blocked  
8. CLI module importable  
9. LangGraph multi-agent pipeline: attack succeeds unsecured, blocked when wrapped  

## Notes

- Install **`inter-agent-guard>=1.1.0`**. The wheel does **not** bundle the ONNX weights (~164 MB INT8); they still ship as [v1.0.0 GitHub Release assets](https://github.com/nizba06/agentguard/releases/tag/v1.0.0).
- Tokenizer files are already in the wheel under `agentguard/models/`.
- Library repo: https://github.com/nizba06/agentguard

## License

Apache-2.0 — see [LICENSE](LICENSE).
