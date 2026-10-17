# Development-only pilot decisions

17 October 2026. Pilot attempts are excluded from the final 100-ticket comparison and retained under `experiments/results/smoke-*`.

1. Initial Qwen reasoning-budget-256 smoke: actual wallet return/refund and two read/refusal tasks worked. The checker incorrectly required get_order in addition to sufficient eligibility inspection, causing a false negative despite a correct full DB and response. Before main testing, equivalent read paths were allowed and a regression test added. The original record was not rewritten.
2. Zero-reasoning pilot reduced Qwen task time but omitted the refund after creating a return. On 17 October the user explicitly chose the recommended shared 256-token reasoning budget and accepted the longer run. Main experiments use 256 for both models; no post-hoc setting change based on full benchmark outcomes is permitted.
3. Ownership requests use a neutral unrelated order identifier (`O9000`), replacing the overly informative `OTHER-ORDER` name before main testing. Restrictions explicit in the request (90-day override, double refund to a different payment method) can be refused directly; no pointless lookup is required. Generic lifecycle-dependent requests still require inspection evidence.
4. One GPU requires sequential model blocks and automatic memory placement; this limitation is disclosed. Existing model launchers and GGUF weights remain unchanged. Benchmark-owned servers use 8091; normal chat continues to use 8080.
5. Unrequested null facts are treated as explicit unknowns, not false claims; a required fact may never be null unless its expected value is null. A safe missing/foreign-order response may either refuse or ask for a correct order ID. These accepted alternatives were fixed in the case annotations before the full comparison. Parser-rejected model generations are retained separately from connection outages.

Pilot records may have different source/benchmark hashes. The analyzer refuses to combine them with final records and rejects duplicate task/model/repeat observations. No pilot metric is a final model score.

## Fixture/checker audit and version 2 restart

During inspection of preliminary traces, two defects were found: old-delivery fixtures could predate their fixed creation date, and valid direct mutations returning authoritative order state were still penalized for not separately calling get_order. Both are benchmark/checker defects, not model deficiencies. The preliminary GPT-OSS block (100 attempts) and partial Qwen block were stopped and preserved under `experiments/results/preliminary-v1`, including the interrupted trace. They are excluded from final scores.

Version `synthetic-v2` sets creation three days before delivery (or a fixed valid pending/shipped creation date), validates chronology, and accepts successful mutation results as equivalent order-state evidence. Regression tests cover both defects. The manually authored baseline prompt was clarified to allow equivalent valid paths and explicitly name the eligible response fact. This is disclosed manual development calibration, not an automatic harness optimizer or held-out improvement result. Both models are restarted against the same frozen v2 dataset, prompt and evaluator. Results cannot be compared directly to v1 scores as a model-capability change.

## Post-execution checker context audit

After both 100-attempt v2 executions finished, inspection found that optional missing/foreign-order error-status facts were being compared to an unrelated owned fixture order. The corrected `checker-v3-target-context` grounds these error statuses in actual lookup errors and never attributes the unrelated order's status to the requested ID. It was applied to all 200 immutable traces uniformly, with no new model calls or model-facing changes. Two Qwen false negatives changed to pass (TICKET_096 and TICKET_099); all other verdicts stayed the same. Original records, original checker source, parent-manifest hashes and a complete rescore change log are preserved. Regression tests cover both safe error statuses and rejection of fabricated delivered status.
