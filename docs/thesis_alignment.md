# Thesis alignment and approved baseline scope

Source: `thesis_revised_1.pdf`, **Evaluation-Driven Adaptive Agent Systems**, Mohamed Yasser and Belal Sherif, October 2026. All 22 PDF pages were extracted and read. The document is a literature review and proposed methodology; none of its cited numerical findings are results of this implementation.

The thesis main research question asks whether offline evaluation feedback improves success/cost/latency through harness adaptation, task-level model routing, and their combination (section 2.1). A comparison between two fixed models alone cannot answer that question.

On 17 October 2026 the user explicitly selected **100-ticket baseline MVP first**, using existing local GPT-OSS 20B and Qwen3 14B GGUF models through llama.cpp. This is the first milestone of thesis Table 7, not completion of the full thesis. The implementation prompt's 100-ticket scope is used without silently changing the thesis's 200-task protocol.

| Thesis objective | Baseline component and evidence | Remaining thesis experiment |
|---|---|---|
| O1: Repeatable stateful benchmark | SQLite reset per attempt; 100 versioned synthetic cases; complete expected state and raw traces; hashes in manifests | New disjoint 100 development / 40 validation / 60 test tasks partitioned by template and entity combinations |
| O2: Validate outcome and diagnosis | Checker and backend fixtures; adversarial side-effect tests; observed error labels linked to steps | Minimum 40 (target 80) independently human-labelled traces, adjudication, precision/recall/F1, exact and ±1-step localization, Cohen's kappa |
| O3: Harness adaptation | Inspectable fixed system prompt and tool descriptions; immutable evaluation contract | Bounded GEPA adapter and search, development-only feedback, validation selection, scalar vs. structured ablation if funded |
| O4: Cost-aware task routing | Real per-model outcome/resource records; model selected via configuration | Input-only predictor; three development repeats/model; validation q_min; Brier score; matched-random and oracle controls |
| O5: Combined adaptation | Baseline records support later interfaces | Full A/B/C/D plus cheap-only cells, frozen E, interaction and adaptation overhead/break-even |

RQ1 needs audited diagnoses and downstream adaptation; current deterministic failure flags are not a validated causal attribution system. RQ2 needs a trained, frozen router and cost constraints; no routing improvement is claimed. RQ3 needs both adaptation components and the full experiment; it is deferred.

Thesis hypotheses H1 (B improves A), H2 (C saves cost within margin and beats matched random), H3 (D is feasible and cheaper than B/C), and H4 (D beats frozen E) remain untested. Baseline runs measure policy-compliant task completion, state correctness, tool errors, attempted policy breaches, latency, token usage, and API charges.

Scope deviations are explicit: 100 baseline cases with one trial/model instead of the planned 200 split tasks and five held-out repeats; eleven narrowly scoped tools instead of about six; structured final-response facts to make answer checks executable; sequential model blocks on a single GPU instead of interleaving models per task. No optimizer/router tuning is performed on these cases. They must not later become the unseen thesis final test set.

The e-commerce schema, exact refund policy, ticket distribution, structured response contract, quantized model choice, inference limits and server port are implementation choices from the supplied prompt/user and engineering judgment. The thesis does not prescribe them. No claim that a 20B MoE is intrinsically stronger than a dense 14B model is made.
