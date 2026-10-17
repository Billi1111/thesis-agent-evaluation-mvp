# Tool reference (policy-v1)

All tools operate on the session's authenticated customer. Identity is bound outside model inputs. Success returns `{ok: true, data: ...}`. Failure returns `{ok: false, error, message, policy_violation}`. Schemas reject extra/missing fields, empty strings and wrong types. All money is integer cents. Executable descriptions and full JSON schemas are in `agent/tools.py`.

| Tool | Required inputs | Data returned | Side effects / tables | Preconditions and possible errors |
|---|---|---|---|---|
| get_customer | none | Customer identity, synthetic email, wallet_cents | None; reads customers | Session customer exists (fixture invariant) |
| get_order | order_id | Order, original payment, items, shipment | None; reads orders/payments/order_items/shipments | Existing owned order; not_found / ownership |
| check_return_eligibility | order_id | eligible, status, age_days, window_days, returnable | None; reads orders | Existing owned order; not_found / ownership |
| create_return | order_id, reason | Updated order/payment | Inserts returns; updates orders to return_requested | Delivered, returnable, 0–30 days, no prior return; ineligible_return / not_found / ownership |
| process_refund | order_id | Updated order/payment | Inserts refunds; updates orders/payments/returns; wallet refunds also update customers and insert wallet_transactions | Paid cancellation or requested return, exactly once, original destination/amount; refund_precondition / not_found / ownership |
| cancel_order | order_id | Updated order/payment | Updates orders to cancelled; paid refunds require a separate process_refund | Pending order; not_cancellable / not_found / ownership |
| get_wallet | none | wallet_cents and transaction list | None; reads customers/wallet_transactions | Session customer exists |
| pay_with_wallet | order_id | Updated order/payment | Debits customers; inserts negative wallet_transactions; updates payments | Pending unpaid order, sufficient balance; payment_precondition / insufficient_funds / not_found / ownership |
| update_shipping_address | order_id, address | Updated order/payment | Updates orders.address | Pending owned order; shipping_locked / not_found / ownership; complete address must be supplied by user |
| create_support_ticket | request | ticket_id, status=open | Inserts support_tickets | Explicit customer escalation request is a task-level authorization constraint; schema validates nonempty text |
| get_refund_status | order_id | refund record or null | None; reads orders/refunds | Existing owned order; not_found / ownership |

Descriptions distinguish return creation from refund execution and cancellation from automatic reimbursement. No amount/destination/customer override is exposed to the LLM. Foreign orders are rejected before their contents are returned. Every mutation is wrapped in a SQLite transaction; unique per-order refund/return and per-reference wallet constraints prevent duplicate side effects. Backend policy checks complement the independent expected-state evaluator; task-specific authorization, complete-address semantics and textual confirmation are additionally assessed through the task assertions and response contract, with free-form message limitations documented.

Unknown tool names return unknown_tool, and invalid JSON/schema arguments return malformed_json/invalid_arguments without mutation. Unexpected DB/server exceptions are infrastructure errors rather than fabricated successful tool outputs. Raw invocation arguments, result, model step and sequential call index are recorded for every executed tool.
