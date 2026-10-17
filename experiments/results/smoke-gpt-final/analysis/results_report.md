# Actual local baseline results

This report is generated from immutable real model run records. It contains no scripted-model benchmark results.

Recorded 3 of 3 planned attempts. Complete planned run: True. A full baseline comparison requires 100 unique tickets per model.

| Model | Attempts | Passed | Success | DB correct | Mean / median / p95 seconds | Mean input / output tokens | API USD |
|---|---:|---:|---:|---:|---|---|---:|
| gpt_oss_20b | 3 | 1 | 33.33% | 100.00% | 4.95 / 3.24 / 8.23 | 3192.67 / 149.33 | 0.00 |
gpt_oss_20b: lowest observed category rates: returns_refunds (0.0%), restricted (0.0%), order_information (100.0%). Infrastructure failures: 0; attempted policy violations: 0. Failure counts: {"incorrect_response": 2}.
Response correctness: 33.3%; inspection-evidence completeness: 100.0%; state plus response correctness: 33.3%.

## Interpretation and limitations

Local inference has zero API charges, so these runs cannot establish a monetary API-cost advantage. Hardware, electricity, and amortization were not measured; latency and token consumption remain useful resource comparisons.

The two models use different architectures, quantization schemes, and their embedded chat templates. Both share the agent, system prompt, tool schemas, fixtures, evaluator, token cap, temperature and seed. A larger parameter count does not establish a stronger model.

Models run in sequential blocks on one GPU. Server load and warm-up time are excluded from per-task latency. Task latency includes all model calls, tools, and execution-loop checks; loading times are retained in runtime logs. GPU placement is automatically fitted and can differ by model.

This 100-ticket baseline has no held-out optimizer/router splits and must not be reused as the thesis final test set. Templates within categories are related. Wilson intervals and task-cluster bootstrap differences are exploratory. One repeat cannot measure pass^5 reliability or statistical stability.

Final answers must satisfy a structured JSON contract, which makes scoring executable but adds formatting difficulty. Requested facts and known extra factual claims are checked; the free-text message is not fully semantically verified. Failure labels describe observable defects, not audited causal diagnoses.

The primary score also includes the predeclared inspection-evidence workflow requirement. A direct valid mutation may produce the correct database but fail this additional workflow check. Database correctness and state-plus-response correctness are reported separately so this stricter harness score is not mistaken for a pure end-state score. Equivalent inspection tools are accepted and no exact call order is required.

Harness optimization, model routing, human diagnostic audit, and the thesis A/B/C/D experiment are deferred by the approved baseline scope. No claims about these research hypotheses are made.

Next steps: audit accepted and failed traces, freeze an unseen 200-task split, repeat attempts, then implement and evaluate GEPA and offline routing with adaptation-cost accounting.
