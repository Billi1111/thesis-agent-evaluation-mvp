# Actual local baseline results

This report is generated from immutable real model run records. It contains no scripted-model benchmark results.

Recorded 200 of 200 planned attempts. Complete planned run: True. A full baseline comparison requires 100 unique tickets per model.

Scoring revision: checker-v3-target-context. Record stage: audited_rescore_from_immutable_real_traces. Audited rescoring preserves original execution records and uses no additional model calls; see the parent rescore_audit.json for the exact changed verdicts.

| Model | Attempts | Passed | Success | DB correct | Mean / median / p95 seconds | Mean input / output tokens | API USD |
|---|---:|---:|---:|---:|---|---|---:|
| qwen3_14b | 100 | 73 | 73.00% | 96.00% | 32.89 / 30.00 / 57.20 | 3864.82 / 635.30 | 0.00 |
| gpt_oss_20b | 100 | 72 | 72.00% | 97.00% | 3.71 / 2.83 / 7.29 | 3012.59 / 124.09 | 0.00 |

Highest observed success: **qwen3_14b**. This is one authored-domain baseline, not evidence that parameter count causes higher capability.

qwen3_14b: lowest observed category rates: order_information (53.3%), multi_step (66.7%), wallet (66.7%). Infrastructure failures: 0; attempted policy violations: 0. Failure counts: {"incorrect_response": 27, "premature_success_claim": 3, "wrong_database_state": 4, "missing_tool_invocation": 2}.
Response correctness: 73.00%; inspection-evidence completeness: 98.00%; state plus response correctness: 73.00%.
Fully metered attempts: 100/100. Token means exclude partial or unavailable usage; observed token totals are lower bounds when usage is incomplete.

gpt_oss_20b: lowest observed category rates: restricted (20.0%), shipping (60.0%), cancellation (66.7%). Infrastructure failures: 0; attempted policy violations: 4. Failure counts: {"incorrect_response": 22, "premature_success_claim": 2, "wrong_database_state": 3, "business_rule_violation": 4, "missing_tool_invocation": 7, "invalid_model_output": 3}.
Response correctness: 78.00%; inspection-evidence completeness: 93.00%; state plus response correctness: 78.00%.
Fully metered attempts: 97/100. Token means exclude partial or unavailable usage; observed token totals are lower bounds when usage is incomplete.

## Observable failure examples

| Model / ticket | Observable defect | Raw trace |
|---|---|---|
| qwen3_14b / TICKET_046 | `{"category": "wrong_database_state", "tables": ["customers", "orders", "payments", "refunds", "wallet_transactions"], "response_errors": ["outcome"], "policy_attempts": []}` | `../../baseline/qwen3_14b/traces/TICKET_046_qwen3_14b_0.jsonl` (inside that model's experiment) |
| qwen3_14b / TICKET_010 | `{"category": "incorrect_response", "tables": [], "response_errors": ["invalid_response_contract"], "policy_attempts": []}` | `../../baseline/qwen3_14b/traces/TICKET_010_qwen3_14b_0.jsonl` (inside that model's experiment) |
| gpt_oss_20b / TICKET_016 | `{"category": "wrong_database_state", "tables": ["customers", "orders", "payments", "refunds", "wallet_transactions"], "response_errors": ["unsupported_fact:status"], "policy_attempts": []}` | `../../baseline/gpt_oss_20b/traces/TICKET_016_gpt_oss_20b_0.jsonl` (inside that model's experiment) |
| gpt_oss_20b / TICKET_051 | `{"category": "incorrect_response", "tables": [], "response_errors": ["outcome", "unsupported_fact:status"], "policy_attempts": []}` | `../../baseline/gpt_oss_20b/traces/TICKET_051_gpt_oss_20b_0.jsonl` (inside that model's experiment) |
| gpt_oss_20b / TICKET_074 | `{"category": "business_rule_violation", "tables": [], "response_errors": [], "policy_attempts": [{"step": 1, "error": "shipping_locked"}]}` | `../../baseline/gpt_oss_20b/traces/TICKET_074_gpt_oss_20b_0.jsonl` (inside that model's experiment) |
| gpt_oss_20b / TICKET_099 | `{"category": "invalid_model_output", "tables": [], "response_errors": ["invalid_response_contract"], "policy_attempts": []}` | `../../baseline/gpt_oss_20b/traces/TICKET_099_gpt_oss_20b_0.jsonl` (inside that model's experiment) |

Paired comparison: `{"gpt_oss_20b minus qwen3_14b": {"paired_tasks": 100, "difference_percentage_points": -1.0, "paired_task_bootstrap_95_pp": [-13.0, 11.0], "resamples": 10000, "interpretation": "Exploratory authored baseline, not confirmatory held-out thesis evidence."}}`

The exploratory paired interval includes zero, so this single run does not establish a directional success-rate difference.

## Interpretation and limitations

Local inference has zero API charges, so these runs cannot establish a monetary API-cost advantage. Hardware, electricity, and amortization were not measured; latency and token consumption remain useful resource comparisons.

The two models use different architectures, quantization schemes, and their embedded chat templates. Both share the agent, system prompt, tool schemas, fixtures, evaluator, token cap, temperature and seed. A larger parameter count does not establish a stronger model.

Native-format parser rejections are reported as model/protocol-format failures. They may involve model output and llama.cpp template/parser compatibility; these observations do not establish an intrinsic reasoning defect. Connection, authentication and other server outages are reported separately as infrastructure failures.

Models run in sequential blocks on one GPU. Server load and warm-up time are excluded from per-task latency. Task latency includes all model calls, tools, and execution-loop checks; loading times are retained in runtime logs. GPU placement is automatically fitted and can differ by model.

This 100-ticket baseline has no held-out optimizer/router splits and must not be reused as the thesis final test set. Templates within categories are related. Wilson intervals and task-cluster bootstrap differences are exploratory. One repeat cannot measure pass^5 reliability or statistical stability.

Final answers must satisfy a structured JSON contract, which makes scoring executable but adds formatting difficulty. Requested facts and known extra factual claims are checked; the free-text message is not fully semantically verified. Failure labels describe observable defects, not audited causal diagnoses.

The primary score includes factual evidence as well as state, response and policy checks. Equivalent read tools and authoritative state returned by successful mutations count as evidence; no redundant lookup or exact call sequence is required. Database correctness and state-plus-response correctness are also reported separately.

Harness optimization, model routing, human diagnostic audit, and the thesis A/B/C/D experiment are deferred by the approved baseline scope. No claims about these research hypotheses are made.

Next steps: audit accepted and failed traces, freeze an unseen 200-task split, repeat attempts, then implement and evaluate GEPA and offline routing with adaptation-cost accounting. For a local cost-aware router, first measure energy/hardware costs or predeclare a resource proxy: identical zero API charges are not informative routing cost labels.
