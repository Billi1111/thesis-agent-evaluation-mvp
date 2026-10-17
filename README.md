# Thesis agent evaluation baseline MVP

Working local tool-agent evaluation built for the supplied **Evaluation-Driven Adaptive Agent Systems** thesis. The approved first milestone is a **100-ticket fixed-harness comparison** of existing Qwen3 14B and GPT-OSS 20B GGUF models. Full GEPA optimization, routing and A/B/C/D experiments are future thesis phases; see [alignment](docs/thesis_alignment.md).

The agent loop is adapted from [Sierra tau-bench](https://github.com/sierra-research/tau-bench/tree/59a200c6d575d595120f1cb70fea53cef0632f6b) (MIT), with a real local OpenAI-compatible model client, eleven tools and a resettable SQLite backend. Upstream's old tasks are not reused. [Selection and source provenance](docs/agent_selection.md).

## Setup on this machine

Run PowerShell in this project folder. Python 3.12+, `uv`, existing CUDA llama.cpp build 10809, the two existing GGUF files and an RTX 3060 12 GB are used. No API key, Docker, database service, model download or paid provider is required.

```powershell
uv --native-tls --cache-dir .uv-cache venv --python 3.12 .venv
uv --native-tls --cache-dir .uv-cache pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m evaluation.runner validate
```

On this device, if Python is not on PATH, supply this installed interpreter to `uv venv --python`:
`C:\Users\bilal\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Normal llama.cpp launchers in `C:\Users\bilal\Documents\ChatGPT\llama.cpp` remain available. Benchmark scripts use port **8091**, separate logs and their own PID, and never edit those launchers or model files. For clean timings, close other GPU-intensive applications and stop normal chat models before benchmarking.

## Run real models

Start with a smoke test (separate output directories preserve all attempts):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/Run-Baseline.ps1 -SmokeOnly -Output experiments/results/my-smoke
```

Run all 100 tickets with each model and generate six PNG/SVG comparisons:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/Run-Baseline.ps1 -Output experiments/results/my-baseline
```

This loads one model at a time. On the local GPU, a complete comparison may take tens of minutes. The command runs the actual models, not replayed or scripted answers. Existing output directories require `-Resume`, which rejects source/configuration changes. Use fresh output directories after making any experimental change. Saved source hashes make full-run comparisons auditable. Interrupted traces are preserved; an interrupted attempt is restarted from a fresh DB and logged separately.

Individual commands:

```powershell
& ./scripts/Start-Benchmark-Model.ps1 -Model qwen3_14b
.venv/Scripts/python.exe -m evaluation.runner run --models qwen3_14b --output experiments/results/qwen-new
& ./scripts/Start-Benchmark-Model.ps1 -Model gpt_oss_20b
.venv/Scripts/python.exe -m evaluation.runner run --models gpt_oss_20b --output experiments/results/gpt-new
& ./scripts/Start-Benchmark-Model.ps1 -Stop
.venv/Scripts/python.exe -m analysis.analyze_results experiments/results/qwen-new experiments/results/gpt-new --output experiments/results/comparison-new
```

`experiments/configs/llamacpp.json` controls model IDs, limits, inference settings and dated local pricing. Optional `.env` overrides are documented in `.env.example`. An Ollama adapter/config is also present for future use, but the installed requested models are GGUF files served by llama.cpp. Models cannot use shell, file or SQL tools; they can call only the listed domain functions.

## Inspect the benchmark and results

- Dataset: `benchmark/tickets.jsonl` (exactly 100 cases with explicit initial/expected state, response facts and assertions).
- Agent/prompt/tools: `agent/tool_calling_agent.py`, `agent/system_prompt.txt`, `agent/tools.py`.
- Schema/business rules: `environment/schema.sql`, `environment/backend.py`, [architecture](docs/system_architecture.md), [tool reference](docs/tools.md).
- Runner/checker: `evaluation/runner.py`, `evaluation/assertions.py`.
- Results: each experiment has `manifest.json`, `runs.jsonl`, `runs.csv`, and observable per-attempt traces with initial/final DB snapshots.
- Analysis: `analysis/analyze_results.py` creates `metrics.json`, combined CSV, `results_report.md`, and six high-resolution PNG/SVG figures from actual logs.
- Integrity audit: `analysis/audit_results.py` verifies all 200 records, matching fixtures/source hashes, repeated state assertions, ledger conservation and refund/payment consistency. The verified sample SQLite database is `environment/sample-v2.sqlite`.
- [Methodology and limitations](docs/experiment_methodology.md), [results status](docs/results_report.md).

The delivered final scores are in `experiments/results/audited-baseline/analysis`: Qwen3 **73/100**, GPT-OSS **72/100**. Both completed 100 actual local attempts. Original execution records/traces remain in `experiments/results/baseline`; an audited checker correction rescored all traces uniformly and changed two false-negative Qwen refusal verdicts. No model-facing code, task, model output or inference setting changed during rescoring. Full provenance is in `experiments/results/audited-baseline/rescore_audit.json`. The current runner uses the corrected checker for new experiments.

Generate a persistent sample SQLite DB for manual inspection, using a new filename if it exists:

```powershell
.venv/Scripts/python.exe -m scripts.export_fixture --ticket TICKET_031 --output environment/inspect.sqlite
```

Rebuild the benchmark only when intentionally creating a new experimental version:

```powershell
.venv/Scripts/python.exe -m benchmark.generate
```

Audit the completed supplied comparison:

```powershell
.venv/Scripts/python.exe -m analysis.audit_results experiments/results/audited-baseline --output experiments/results/audited-baseline/analysis/audit.json
```

Recreate the supplied audited scores from the preserved original executions (use a new output directory):

```powershell
.venv/Scripts/python.exe -m analysis.rescore experiments/results/baseline --output experiments/results/audit-reproduction
.venv/Scripts/python.exe -m analysis.analyze_results experiments/results/audit-reproduction/qwen3_14b experiments/results/audit-reproduction/gpt_oss_20b --output experiments/results/audit-reproduction/analysis
```

The evaluator verifies every table, prevents unrelated changes from hiding behind a correct target status, and requires an accurate structured final outcome. Tests use scripted completions only to validate infrastructure. These are never saved as model comparison results. API charges for local inference are zero; hardware/electricity cost is unmeasured. A single run is exploratory and cannot establish repeated reliability or answer the thesis adaptation/routing hypotheses.
