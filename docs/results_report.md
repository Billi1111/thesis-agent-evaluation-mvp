# Verified baseline results

All 200 main attempts completed using the existing local GGUF files: 100 tickets per model, one trial each, identical fixtures/tools/harness/settings. No infrastructure failures occurred. **137 automated tests pass.**

| Model | Audited full task success | DB correctness | Mean / median / p95 latency | Mean input / output tokens | Local API charge |
|---|---:|---:|---|---|---:|
| Qwen3 14B Q4_K_M | 73/100 | 96/100 | 32.89 / 30.00 / 57.20 s | 3864.82 / 635.30 | $0 |
| GPT-OSS 20B UD-Q4_K_XL | 72/100 | 97/100 | 3.71 / 2.83 / 7.29 s | 3012.59 / 124.09 | $0 |

The one-percentage-point success difference is inconclusive: the exploratory paired task-bootstrap 95% interval for GPT-OSS minus Qwen is **[-13, +11] percentage points**. GPT-OSS was approximately 8.86 times faster in mean task latency on this device. This is a system/quantization/template comparison, not a causal parameter-count experiment. GPT token means cover 97 fully metered attempts; three native-format parser rejections have incomplete usage. Hardware/electricity costs are unmeasured.

Qwen had zero prohibited mutation attempts; GPT had four, all blocked by the backend. Both models sometimes reached correct DB state but returned incorrect facts or the wrong structured outcome. Qwen's lowest category was information retrieval (53.3%); GPT's was restricted operations (20%). Refusal formatting and native parser compatibility contribute to these rates, so they should not be interpreted as pure reasoning capability.

Primary final artifacts: `experiments/results/audited-baseline/analysis/results_report.md`, `metrics.json`, `runs.csv`, `audit.json`, and `plots/` (six high-resolution PNG plus six SVG charts). Corrected per-model scored records are under `experiments/results/audited-baseline/{model}`; actual original calls, responses and DB snapshots remain under `experiments/results/baseline/{model}/traces`.

The final audit found a checker context defect: missing/foreign-order error-status facts were compared with an unrelated fixture order. The correction was applied uniformly to all 200 immutable traces, with zero additional model calls. Exactly two Qwen verdicts changed from fail to pass (TICKET_096 and TICKET_099); GPT stayed at 72. Original verdicts remain unchanged under `baseline/`; the original checker source is preserved there too. `audited-baseline/rescore_audit.json` lists both changes, and derived manifests link and hash their original provenance.

The integrity audit rechecked all verdicts, verified 100 identical initial-state pairs, confirmed model-facing sources stayed fixed, and found no wallet-ledger, refund/payment or unrelated-entity invariant violations. This does not imply every task passed: incomplete requested operations and inaccurate responses are retained as failures.

Scope and limitations: this is the approved authored 100-ticket baseline. Related templates, one trial, strict typed response contracts, sequential GPU model blocks and different quantizations limit generalization. Full GEPA optimization, model routing, human diagnostic audit, fresh 200-task split and repeated A/B/C/D experiments are deferred. For local cost-aware routing, measure energy/hardware costs or predeclare a resource proxy; zero API charges cannot distinguish model costs.
