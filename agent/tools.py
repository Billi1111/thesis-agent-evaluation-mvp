"""Tool schemas are shared unchanged by every evaluated model."""
from jsonschema import Draft202012Validator, ValidationError
from environment.backend import BusinessError

DEFINITIONS = [
    ('get_customer', 'Inspect the authenticated customer, including wallet balance in cents.', {}),
    ('get_order', 'Inspect your order, payment, line items and shipment. Does not mutate state.', {'order_id':'string'}),
    ('check_return_eligibility', 'Check whether a delivered order is returnable within the 30-day window.', {'order_id':'string'}),
    ('create_return', 'Request a full return of an eligible delivered order. Does not refund it.', {'order_id':'string','reason':'string'}),
    ('process_refund', 'Refund a paid cancelled order or requested return exactly once to the original payment method. Amount is determined by the backend.', {'order_id':'string'}),
    ('cancel_order', 'Cancel a pending order. Paid orders still need process_refund afterwards.', {'order_id':'string'}),
    ('get_wallet', 'Get your wallet balance in cents and all wallet transactions.', {}),
    ('pay_with_wallet', 'Pay a pending unpaid order in full from your wallet if sufficient funds exist.', {'order_id':'string'}),
    ('update_shipping_address', 'Change a pending order address before shipment; use the exact complete address supplied by the customer.', {'order_id':'string','address':'string'}),
    ('create_support_ticket', 'Create an open support ticket using a concise description of the requested escalation.', {'request':'string'}),
    ('get_refund_status', 'Inspect a completed refund for your order, or return null if absent.', {'order_id':'string'}),
]
TOOLS = [{'type':'function','function':{'name':n,'description':d,'parameters':{
    'type':'object','properties':{k:{'type':v,'minLength':1} for k,v in p.items()},
    'required':list(p),'additionalProperties':False}}} for n,d,p in DEFINITIONS]
SCHEMAS = {t['function']['name']:t['function']['parameters'] for t in TOOLS}


def execute(backend, customer, name, args):
    if name not in SCHEMAS:
        return {'ok':False,'error':'unknown_tool','message':'Tool is not available','policy_violation':False}
    try:
        Draft202012Validator(SCHEMAS[name]).validate(args)
        return {'ok':True,'data':backend.invoke(customer,name,args)}
    except ValidationError as exc:
        return {'ok':False,'error':'invalid_arguments','message':exc.message,'policy_violation':False}
    except BusinessError as exc:
        return {'ok':False,'error':exc.code,'message':str(exc),'policy_violation':exc.policy}
