# inter-agent-guard — PyPI validation demo

Standalone project that installs **`inter-agent-guard`** from PyPI (not a local clone) and validates the library works.

| PyPI install name | Python import |
|-------------------|---------------|
| `inter-agent-guard` | `agentguard` |

## Setup

```powershell
cd inter-agent-guard-demo

# Optional: fresh venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install inter-agent-guard
```

## Run validation

```powershell
py -3.12 run_validation.py
```

Checks:

1. Import `agentguard` + version
2. Load YAML manifests (JSON Schema from bundled package)
3. Block prompt injection via `inspect_message()`
4. Forward benign inter-agent messages
5. Capability enforcement (`publish_external` denied)
6. MCP tool output poisoning blocked
7. CLI module importable

Also try the CLI:

```powershell
agentguard status
agentguard inspect -m "Summarise public pricing from filings."
```

## Notes

- ML model (`risk_scorer.onnx`) is optional for this demo — rule filter handles injection tests.
- For production enforce-mode with ML, download ONNX from [GitHub Releases](https://github.com/nizba06/agentguard/releases).
