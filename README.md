# inter-agent-guard — PyPI validation demo

Standalone project that installs **`inter-agent-guard`** from PyPI (not a local clone) and validates the library works **with the ONNX ML model** from GitHub Releases.

| PyPI install name | Python import |
|-------------------|---------------|
| `inter-agent-guard` | `agentguard` |

## Setup

```powershell
cd inter-agent-guard-demo

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install "inter-agent-guard>=1.1.0"
# Optional Poetry: after 1.1.0 is on PyPI → poetry lock && poetry install
```

### Install ML model (required for enforce-mode)

Downloads `risk_scorer.onnx` + `model.sha256` from the public **v1.0.0** GitHub
release (ONNX assets; package version is 1.1.x) into the installed package
`models/` directory and verifies the SHA-256:

```powershell
py -3.12 install_model.py
# re-download: py -3.12 install_model.py --force
```

`install_model.py` uses public HTTPS first, then falls back to `gh release download` / `GH_TOKEN` if needed.

## Run validation

```powershell
py -3.12 run_validation.py
```

`run_validation.py` calls `install_model.py` automatically if the ONNX file is missing, then runs with `require_ml_model=True` (fails if `ModelNotLoadedWarning` would have been raised).

Checks:

1. Import `agentguard` + version
2. ONNX install + hash verify + ML scorer loaded
3. Load YAML manifests (JSON Schema from bundled package)
4. Block prompt injection via `inspect_message()`
5. Forward benign inter-agent messages
6. Capability enforcement (`publish_external` denied)
7. MCP tool output poisoning blocked
8. CLI module importable

Also try the CLI:

```powershell
py -3.12 -m agentguard status
py -3.12 -m agentguard inspect -m "Summarise public pricing from filings."
```

## Notes

- Install **`inter-agent-guard>=1.1.0`**. The wheel does **not** bundle the ONNX weights (~164 MB INT8); they still ship as [v1.0.0 GitHub Release assets](https://github.com/nizba06/agentguard/releases/tag/v1.0.0).
- Tokenizer files are already in the wheel under `agentguard/models/`.
- Library repo: https://github.com/nizba06/agentguard

## License

Apache-2.0 — see [LICENSE](LICENSE).
