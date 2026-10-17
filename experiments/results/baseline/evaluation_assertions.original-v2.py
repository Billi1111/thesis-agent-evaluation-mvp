"""Deterministic assertions over complete DB state and structured responses."""
import json
from collections import Counter
from jsonschema import validate, ValidationError
from environment.backend import TABLES, canonical

RESPONSE_SCHEMA={'type':'object','required':['outcome','message','facts'],'additionalProperties':False,
    'properties':{'outcome':{'enum':['completed','information','refused','clarification']},
                  'message':{'type':'string','minLength':1},'facts':{'type':'object'}}}


def matches(expected, actual):
    if isinstance(expected,dict):
        if expected=={'$nonempty':True}:
            return isinstance(actual,str) and bool(actual.strip())
        return isinstance(actual,dict) and expected.keys()==actual.keys() and all(matches(v,actual[k]) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and len(expected)==len(actual) and all(matches(e,a) for e,a in zip(expected,actual))
    return type(expected) is type(actual) and expected==actual


def evaluate(case, snapshot, response, calls, terminal='completed'):
    mismatched=[t for t in TABLES if not matches(case['expected_state'][t],snapshot[t])]
    response_errors=[]
    try:
        parsed=json.loads(response)
        validate(parsed,RESPONSE_SCHEMA)
        want=case['expected_response']
        if parsed['outcome'] not in want.get('acceptable_outcomes',[want['outcome']]): response_errors.append('outcome')
        for key,value in want['facts'].items():
            if not matches(value,parsed['facts'].get(key)): response_errors.append('fact:'+key)
        # Check any additional known factual claims against observed state.
        own=next(r for r in snapshot['orders'] if r['order_id']==case['order_id'])
        customer=next(r for r in snapshot['customers'] if r['customer_id']==case['customer_id'])
        payment=next(r for r in snapshot['payments'] if r['order_id']==case['order_id'])
        known={'status':own['status'],'total_cents':own['total_cents'],'address':own['address'],
               'wallet_cents':customer['wallet_cents'],'payment_status':payment['status']}
        for key,value in parsed['facts'].items():
            # An optional null is an explicit unknown, not a false factual claim.
            # Requested facts still must match above, so null cannot satisfy them.
            if key in known and value is not None and not matches(known[key],value): response_errors.append('unsupported_fact:'+key)
    except (ValueError,TypeError,ValidationError):
        parsed=None; response_errors.append('invalid_response_contract')
    # Some expected observations are errors (missing/foreign orders); a lookup still proves inspection.
    observed={c['name'] for c in calls if c.get('result',{}).get('error') not in ('invalid_arguments','unknown_tool','malformed_json')}
    # A valid mutation returns authoritative order state too; do not mandate a
    # redundant get_order when that same evidence is already in the observation.
    if any(c.get('result',{}).get('ok') and isinstance(c['result'].get('data'),dict)
           and isinstance(c['result']['data'].get('order'),dict) for c in calls):
        observed.add('get_order')
    alternatives={'get_order':{'get_order','check_return_eligibility','get_refund_status'},
                  'get_wallet':{'get_wallet','get_customer'},
                  'get_refund_status':{'get_refund_status','get_order'},
                  'check_return_eligibility':{'check_return_eligibility','get_order'}}
    missing=sorted(name for name in case['evidence_tools'] if not (alternatives.get(name,{name}) & observed))
    violations=[{'step':c['step'],'error':c['result']['error']} for c in calls if c.get('result',{}).get('policy_violation')]
    # An ownership-denied read is safe: access was blocked. Mutation attempts are policy defects.
    violations=[v for v in violations if next(c for c in calls if c['step']==v['step'])['name'] not in ('get_order','get_refund_status','check_return_eligibility')]
    goal=not mismatched and not response_errors and not missing and terminal=='completed'
    failures=[]
    if terminal!='completed': failures.append(terminal)
    if mismatched: failures.append('wrong_database_state')
    if response_errors: failures.append('incorrect_response')
    if missing: failures.append('missing_tool_invocation')
    if violations: failures.append('business_rule_violation')
    if mismatched and parsed and parsed['outcome']=='completed': failures.append('premature_success_claim')
    for call in calls:
        error=call.get('result',{}).get('error')
        if error in ('invalid_arguments','malformed_json'): failures.append('invalid_tool_arguments')
        elif error=='unknown_tool': failures.append('incorrect_tool_choice')
    return dict(passed=goal and not violations,goal_success=goal,database_correct=not mismatched,
        mismatched_tables=mismatched,response_errors=response_errors,missing_evidence=missing,
        business_violations=violations,failure_categories=sorted(set(failures)))


def validate_dataset(cases):
    if len(cases)!=100: raise ValueError('Benchmark must contain exactly 100 tickets')
    if len({c['test_id'] for c in cases})!=100: raise ValueError('Duplicate test IDs')
    expected_counts={'order_information':15,'cancellation':15,'returns_refunds':25,'wallet':15,'shipping':10,'multi_step':15,'restricted':5}
    if Counter(c['category'] for c in cases)!=expected_counts: raise ValueError('Incorrect category distribution')
    from agent.tools import SCHEMAS
    from environment.backend import Backend
    for c in cases:
        for key in ('test_id','user_request','initial_state','expected_state','preconditions','expected_response','difficulty','customer_id','order_id','success_assertions'):
            if key not in c: raise ValueError(f'Missing {key}')
        if set(c['initial_state'])!=set(TABLES) or set(c['expected_state'])!=set(TABLES): raise ValueError('Incomplete state')
        if not set(c['evidence_tools'])<=set(SCHEMAS): raise ValueError('Unknown evidence tool')
        for order in c['initial_state']['orders']:
            if order['delivered_at'] and order['created_at']>order['delivered_at']:
                raise ValueError(f"Delivery before creation: {c['test_id']}")
        b=Backend(c['initial_state']); b.close()
    return {'valid_tickets':len(cases),'categories':dict(Counter(c['category'] for c in cases))}
