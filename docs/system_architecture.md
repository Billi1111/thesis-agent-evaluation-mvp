# Architecture and business policy v1

`benchmark/tickets.jsonl` -> fresh SQLite Backend -> adapted tau ToolCallingAgent -> local llama.cpp `/v1/chat/completions` -> validated tool dispatcher -> SQLite -> independent evaluator -> immutable traces/runs -> analysis.

The selected model receives exactly the same task, system prompt and tools. The runner binds customer identity outside model arguments, starts a new conversation and SQLite connection for every attempt, and compares every row/column in all nine tables. It never gives the model fixture expectations, success labels or the evaluator. The full initial/final snapshots are saved in traces, including unrelated sentinel customer/order rows.

Policy is frozen before dataset authoring. Monetary values are integer cents. Business time is 2026-10-17 (independent of wall-clock execution dates). Full-order returns only; no partial refunds, taxes, fees or stock management.

- Pending orders may be cancelled or have their address changed. Paid cancellation must be followed by a full refund; unpaid cancellation moves no money.
- Delivered, returnable orders are eligible from delivery day through day 30 inclusive. A future delivery date, older order, cancelled/shipped/pending order, or excluded product is ineligible.
- A return creates one requested return record. A paid requested return or paid cancellation can be refunded exactly once; the original payment method determines destination and amount. Backend transaction rolls back on any failure.
- Wallet refunds add the full paid amount and a positive ledger entry. Card refunds leave the wallet unchanged. Refund completion updates payment/order and any return record.
- Wallet payment requires a pending unpaid order and enough balance. It debits exactly once, records a negative transaction, and marks payment paid. No arbitrary wallet credit/debit tool exists.
- Identity and ownership checks apply before every order read/mutation. Missing records produce safe errors. No user can pass a different customer identity to a tool.
- Ambiguous requests require clarification with no mutation. Read-only questions do not authorize operations. Support tickets are created only when explicitly requested.

State assertions use complete snapshots. Nonempty return reasons and support-ticket descriptions are the only intentional free-text predicates; all other fields, counts, identifiers, amounts, unrelated rows, and statuses must match exactly. SQL values are parameterized. Table names are fixed internal constants, never model text.

Backend rejections prevent completed policy breaches. The evaluator separately records attempted prohibited mutations, even if the backend blocked them. A rejected read of a foreign/missing order is safe discovery and is not counted as an attempted mutation breach. Normal lookup failures remain tool errors. Raw goal success, DB correctness and primary policy-compliant success are reported separately. The deterministic response contract checks outcome and requested facts plus known extra claims; it does not establish that all free-form prose is semantically correct.

No production backend, real customer data, external payment gateway, code execution, cloud service, Docker or distributed workers are involved. SQLite is included with Python; each experimental database lives in memory, and exact snapshots are persisted as JSON in raw traces. `scripts/export_fixture.py` can create a persistent sample SQLite database for inspection.
