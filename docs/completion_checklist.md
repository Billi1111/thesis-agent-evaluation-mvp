# Deliverable checklist

The approved scope is the fixed-harness 100-ticket baseline, not the full thesis experiment.

- [x] Entire thesis read and mapped; objectives/hypotheses and deferred phases explicit.
- [x] Three existing agent implementations inspected; selected source, license and commit recorded.
- [x] Existing MIT tool-calling loop adapted and executed with actual local inference.
- [x] Local Python environment installed; pinned dependencies and optional environment configuration documented.
- [x] SQLite policy backend, synthetic fixtures and independently authored state expectations operational.
- [x] Eleven real tools connected; schemas, outputs, side effects and error conditions documented.
- [x] Exactly 100 executable benchmark cases with deterministic reset and assertions validated.
- [x] Automated isolation, bounded inference/tool calls, observable traces, usage and state snapshots implemented.
- [x] Local model configuration and dedicated safe model launcher implemented; normal launchers unchanged.
- [x] Backend/tool/evaluator/analysis tests pass (137 tests including final audit regressions).
- [x] Both models exercised in development smoke tests; pilot decisions and original failures preserved.
- [x] Complete 100-attempt GPT-OSS run: 72 audited passes; 97 correct database states.
- [x] Complete 100-attempt Qwen3 run: 73 audited passes; 96 correct database states.
- [x] Final CSV/JSON scores, six PNG/SVG charts and comparison report generated from actual records; integrity audit passes for all 200 attempts and 100 identical fixture pairs.
- [x] Original traces/records preserved separately from the disclosed final checker rescore; benchmark model servers stopped and GPU released.

Deferred by user-approved scope: GEPA/DSPy harness optimization, diagnostic human audit, offline router training, template-separated development/validation/test tasks, five test repetitions, A/B/C/D/frozen/random/oracle controls and offline adaptation accounting. These are not implemented or represented as completed.
