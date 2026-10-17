import copy
import json
import pytest
from benchmark.generate import build_cases
from evaluation.assertions import evaluate,validate_dataset
from evaluation.runner import load_cases
from environment.backend import Backend
from agent.tools import execute


def calls_for(case):
    return [{'step':i+1,'name':name,'result':{'ok':True}} for i,name in enumerate(case['evidence_tools'])]


@pytest.mark.parametrize('case',build_cases(),ids=lambda c:c['test_id'])
def test_all_expectations_are_executable(case):
    # Apply an authored action plan to the real DB, then compare to independent expected data.
    b=Backend(case['initial_state']); target=case['expected_state']; initial=case['initial_state']; oid=case['order_id']
    actions=[]
    if target['returns'] and not initial['returns']: actions.append(('create_return',{'order_id':oid,'reason':'damaged'}))
    if target['orders'][0]['status'] in ('cancelled','refunded') and initial['orders'][0]['status']=='pending': actions.append(('cancel_order',{'order_id':oid}))
    if len(target['refunds'])>len(initial['refunds']): actions.append(('process_refund',{'order_id':oid}))
    if target['payments'][0]['status']=='paid' and initial['payments'][0]['status']=='unpaid': actions.append(('pay_with_wallet',{'order_id':oid}))
    if target['orders'][0]['address']!=initial['orders'][0]['address']: actions.append(('update_shipping_address',{'order_id':oid,'address':target['orders'][0]['address']}))
    if target['support_tickets']: actions.append(('create_support_ticket',{'request':'Please investigate requested exception'}))
    for name,args in actions: assert execute(b,case['customer_id'],name,args)['ok']
    response=json.dumps({'outcome':case['expected_response']['outcome'],'facts':case['expected_response']['facts'],'message':'Fixture checker test, not a model response.'})
    result=evaluate(case,b.snapshot(),response,calls_for(case))
    assert result['passed'],result
    b.close()


def test_generated_dataset_matches_versioned_artifact():
    cases=load_cases('benchmark/tickets.jsonl')
    assert cases==build_cases(); assert validate_dataset(cases)['valid_tickets']==100


def test_false_success_and_unrelated_mutation_are_rejected():
    c=build_cases()[15]; b=Backend(c['initial_state'])
    r=evaluate(c,b.snapshot(),json.dumps({'outcome':'completed','message':'Refund complete','facts':{}}),calls_for(c))
    assert not r['passed']; assert 'premature_success_claim' in r['failure_categories']; b.close()
    c=build_cases()[0]; altered=copy.deepcopy(c['expected_state']); altered['customers'][1]['wallet_cents']+=1
    r=evaluate(c,altered,json.dumps({**c['expected_response'],'message':'Information'}),calls_for(c))
    assert not r['database_correct']; assert not r['passed']


def test_clarification_requires_no_mutation_and_correct_outcome():
    c=next(c for c in build_cases() if c['expected_response']['outcome']=='clarification')
    assert evaluate(c,c['initial_state'],json.dumps({'outcome':'clarification','message':'Which order?','facts':{}}),[])['passed']
    assert not evaluate(c,c['initial_state'],json.dumps({'outcome':'completed','message':'Done','facts':{}}),[])['passed']


def test_prose_or_wrong_facts_cannot_pass():
    c=build_cases()[0]
    for response in ['Done',json.dumps({'outcome':'information','message':'Status','facts':{'status':'shipped'}})]:
        assert not evaluate(c,c['initial_state'],response,calls_for(c))['passed']


def test_expected_snapshot_does_not_hide_extra_rows():
    c=build_cases()[0]; altered=copy.deepcopy(c['expected_state'])
    altered['refunds'].append({'refund_id':'extra'})
    assert not evaluate(c,altered,json.dumps({**c['expected_response'],'message':'Status'}),calls_for(c))['passed']


def test_equivalent_inspection_path_is_accepted():
    c=build_cases()[0]
    calls=[{'step':1,'name':'check_return_eligibility','result':{'ok':True}}]
    response=json.dumps({**c['expected_response'],'message':'Status was inspected'})
    assert evaluate(c,c['expected_state'],response,calls)['passed']


def test_optional_unknown_fact_is_not_a_false_claim_but_required_null_fails():
    c=build_cases()[0]
    response={'outcome':'information','message':'Pending','facts':{'status':'pending','wallet_cents':None}}
    assert evaluate(c,c['expected_state'],json.dumps(response),calls_for(c))['passed']
    response['facts']['status']=None
    assert not evaluate(c,c['expected_state'],json.dumps(response),calls_for(c))['passed']


def test_direct_valid_mutation_supplies_order_evidence():
    c=next(c for c in build_cases() if c['category']=='shipping' and c['expected_response']['outcome']=='completed')
    b=Backend(c['initial_state'])
    result=execute(b,c['customer_id'],'update_shipping_address',{'order_id':c['order_id'],'address':'85 Palm Avenue, Alexandria 21500'})
    response=json.dumps({'outcome':'completed','message':'Address changed','facts':{}})
    assessment=evaluate(c,b.snapshot(),response,[{'step':1,'name':'update_shipping_address','result':result}])
    assert assessment['passed']; b.close()


def test_fixture_delivery_never_precedes_creation():
    for c in build_cases():
        for o in c['initial_state']['orders']:
            assert not o['delivered_at'] or o['created_at']<=o['delivered_at']


@pytest.mark.parametrize('ticket,code,status',[('TICKET_099','not_found','not_found'),('TICKET_096','ownership','ownership_error')])
def test_missing_or_foreign_error_facts_do_not_use_unrelated_fixture_order(ticket,code,status):
    c=next(c for c in build_cases() if c['test_id']==ticket)
    calls=[{'step':1,'name':'get_order','result':{'ok':False,'error':code,'policy_violation':code=='ownership'}}]
    response={'outcome':'refused','message':'Cannot find or access that order','facts':{'status':status}}
    assert evaluate(c,c['expected_state'],json.dumps(response),calls)['passed']
    response['facts']['status']='delivered'
    assert not evaluate(c,c['expected_state'],json.dumps(response),calls)['passed']
