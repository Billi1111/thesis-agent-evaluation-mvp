# Verified real tool execution

Preliminary integration attempt `TICKET_035_gpt_oss_20b_0` used the real local GPT-OSS GGUF through llama.cpp. Its preserved observable trace is `experiments/results/preliminary-v1/gpt_oss_20b/traces/TICKET_035_gpt_oss_20b_0.jsonl`.

The model selected and executed get_order, check_return_eligibility, create_return, and process_refund. The SQLite snapshots independently show wallet balance changing from **12000 to 19295 cents**, one completed wallet refund of **7295 cents** (`REF-O035`), a corresponding ledger entry, and the expected final order/payment/return statuses. The complete state checker accepted every table; no response error, missing evidence, or prohibited mutation was recorded. This is an actual model-generated workflow, not a scripted completion.

This example establishes integration, not an overall model success rate. Failed attempts are retained alongside successful ones and counted in the final comparison.
