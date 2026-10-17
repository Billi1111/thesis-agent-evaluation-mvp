# Resume checkpoint — 2026-10-17

## Status

The approved 100-ticket baseline MVP is COMPLETE. Both local models finished all 100 attempts (200 total); final results, plots, documentation and integrity checks are delivered. No inference job needs resuming. Last verification: 137 tests passed. Benchmark servers have been stopped.

GitHub backup requested by the user: private repository Billi1111/thesis-agent-evaluation-mvp, branch main. Confirm upload with `git remote -v` and `git status` when resuming. Local runtime environments, model weights, caches, SQLite files and server logs are excluded. `.gitattributes` preserves exact file bytes so recorded experiment hashes remain valid across checkouts.

Read this file, README.md, docs/results_report.md and docs/completion_checklist.md before continuing. Do not rerun the experiment or begin the deferred thesis phase without a new user request.

## User decisions

- Implement the 100-ticket fixed-harness baseline first; full thesis optimization and routing are deferred.
- Use existing local Qwen3 14B and GPT-OSS 20B through llama.cpp, with no paid APIs or model downloads.
- Use a shared 256-token reasoning budget, accepting longer runs.
- Preserve normal model launchers and allow the user to open the models normally.
- User requested a durable checkpoint in case chat/account limits interrupt future work.

## Final verified results

| Metric | Qwen3 14B | GPT-OSS 20B |
| --- | ---: | ---: |
| Attempts | 100 | 100 |
| Task success | 73% | 72% |
| Correct final DB state | 96% | 97% |
| Mean task latency | 32.893 s | 3.714 s |
| Fully metered attempts | 100 | 97 |
| Prohibited mutation attempts | 0 | 4 (all blocked) |
| Infrastructure failures | 0 | 0 |
| API charges | $0 | $0 |

GPT was about 8.86 times faster on this setup. Success difference is inconclusive: GPT minus Qwen = -1 percentage point, exploratory paired bootstrap 95% interval [-13, +11] points. Hardware/electricity cost was not measured. Three GPT native-format parser rejections have incomplete token usage; observed totals are lower bounds. One trial, related synthetic templates, different quantizations and model architectures limit generalization.

Primary deliverables:

- docs/results_report.md — concise final report.
- experiments/results/audited-baseline/ — FINAL scored results, derived manifests, rescore audit.
- experiments/results/audited-baseline/analysis/ — metrics.json, runs.csv, results_report.md, audit.json, six PNG and six SVG plots.
- experiments/results/baseline/ — immutable original real executions, raw traces and original manifests.
- docs/thesis_alignment.md, docs/experiment_methodology.md, docs/agent_selection.md — scope and provenance.

## Important scoring provenance

Final results use checker-v3-target-context. A post-run audit found that optional status on missing/foreign-order errors was compared against an unrelated owned fixture order. The correction grounds such status in actual tool errors. All 200 original executions were uniformly rescored WITHOUT any new model calls. Only Qwen TICKET_096 and TICKET_099 changed from fail to pass (71 -> 73); GPT remained 72. Original executions and verdicts remain untouched. Original checker snapshot: experiments/results/baseline/evaluation_assertions.original-v2.py.

Audit audited-baseline with the current checker. Do not present original baseline verdicts or preliminary-v1 runs as final results. The earlier preliminary-v1 runs had fixture chronology and overly strict redundant-inspection checks; they are preserved solely as preliminary provenance.

Final audit revalidated all 200 verdicts, 100 identical paired initial states, unchanged model-facing sources during inference, wallet/refund consistency and unrelated-entity preservation. It found no invariant breaches.

## Local runtime and implementation

- Workspace: C:\Users\bilal\Desktop\Grad Project\MVP
- Python: .venv\Scripts\python.exe (3.12.14); pinned requirements.txt.
- llama.cpp: C:\Users\bilal\Documents\ChatGPT\llama.cpp\bin\llama-server.exe
- Runtime: build 10809, commit 5266f24da; RTX 3060 12 GB.
- Qwen weights: C:\Users\bilal\Desktop\Local Models\Qwen3-14B-Q4_K_M.gguf
- GPT weights: C:\Users\bilal\Documents\ChatGPT\llama.cpp\models\gpt-oss-20b-UD-Q4_K_XL.gguf
- Dedicated benchmark port 8091; normal chat port 8080 and existing launchers untouched.
- Runtime metadata, hashes and launch arguments: experiments/runtime/.
- Shared config: experiments/configs/llamacpp.json; temperature 0, seed 42, context 8192, output 2048 per call, reasoning budget 256, maximum 12 model steps / 16 tools, concurrency 1.
- Adapted Sierra tau-bench loop (MIT), commit 59a200c6d575d595120f1cb70fea53cef0632f6b. Source/license/provenance are preserved. Old upstream tickets were not reused.
- Eleven schema-validated tools, reset-per-attempt SQLite, bound customer identity, exactly 100 synthetic-v2 tickets. Complete expected snapshots and structured response facts are checked; free-text semantic correctness is not fully verified.
- agent/: loop, real local model client, tools, fixed prompt.
- environment/: backend and schema; current sample DB sample-v2.sqlite.
- benchmark/: fixtures and independently specified expected states.
- evaluation/: runner, current assertions, manifests and resumability.
- analysis/: rescore, report generation and integrity audit.
- scripts/: hidden dedicated model launcher, sequential baseline runner and fixture export.

## Commands if requested later

Run from the workspace in PowerShell. No rerun is needed to complete the current milestone.

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m evaluation.runner validate
.venv/Scripts/python.exe -m analysis.audit_results experiments/results/audited-baseline --output experiments/results/audited-baseline/analysis/audit.json
```

Reproduce inference into a NEW directory (close other GPU workloads for clean timing):

```powershell
& ./scripts/Run-Baseline.ps1 -Output experiments/results/reproduction -Models gpt_oss_20b,qwen3_14b
```

Reproduce final scoring without model calls into a NEW directory:

```powershell
.venv/Scripts/python.exe -m analysis.rescore experiments/results/baseline --output experiments/results/audit-reproduction
.venv/Scripts/python.exe -m analysis.analyze_results experiments/results/audit-reproduction/qwen3_14b experiments/results/audit-reproduction/gpt_oss_20b --output experiments/results/audit-reproduction/analysis
```

The runner supports -Resume only for unchanged sources/configuration, and resets interrupted attempts to a fresh DB while preserving interrupted traces. Do not overwrite delivered results.

## Deferred thesis work

Not started: GEPA/DSPy harness optimization, human trace diagnosis, offline routing, fresh template-disjoint 200-task split (100 development / 40 validation / 60 test), repeated trials/pass5, A/B/C/D and routing controls, adaptation costs/break-even. A cost-aware local router would need measured energy/hardware costs or an explicitly agreed proxy because both API charges are zero.

Original instructions: C:\Users\bilal\.codex\attachments\a53e1135-c480-4bc7-a137-a8f269c33355\Pasted text.txt. Thesis: thesis_revised_1.pdf in workspace, fully read during implementation.

## Suggested prompt for a new chat

"Read HANDOFF.md and README.md in C:\Users\bilal\Desktop\Grad Project\MVP, then review docs/results_report.md. The baseline is already complete; preserve the delivered executions and results. Continue with my next requested change from this checkpoint."
