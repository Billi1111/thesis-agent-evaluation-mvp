import copy
import pytest
from benchmark.generate import fixture
from environment.backend import Backend,BusinessError
from agent.tools import execute


def test_refund_atomic_exact_once_and_unrelated_state():
    b=Backend(fixture(1)); start=b.snapshot()
    b.invoke('C001','create_return',{'order_id':'O001','reason':'damaged'})
    b.invoke('C001','process_refund',{'order_id':'O001'})
    after=b.snapshot()
    assert after['customers'][0]['wallet_cents']==12000+2637
    assert after['customers'][1]==start['customers'][1]
    assert after['orders'][1]==start['orders'][1]
    assert len(after['refunds'])==len(after['wallet_transactions'])==1
    with pytest.raises(BusinessError): b.invoke('C001','process_refund',{'order_id':'O001'})
    assert b.snapshot()==after
    b.close()


@pytest.mark.parametrize('age,allowed',[(0,True),(30,True),(31,False),(-1,False)])
def test_return_window(age,allowed):
    b=Backend(fixture(1,age=age)); assert b.eligible('C001','O001')['eligible']==allowed; b.close()


def test_card_refund_does_not_credit_wallet():
    b=Backend(fixture(1,method='card',status='cancelled'))
    b.invoke('C001','process_refund',{'order_id':'O001'})
    assert b.snapshot()['customers'][0]['wallet_cents']==12000
    assert not b.snapshot()['wallet_transactions']; b.close()


@pytest.mark.parametrize('name,args',[
    ('create_return',{'order_id':'O9000','reason':'bad'}),
    ('process_refund',{'order_id':'O001'}),
    ('pay_with_wallet',{'order_id':'O001'}),
    ('cancel_order',{'order_id':'O001'}),
    ('update_shipping_address',{'order_id':'O001','address':'Elsewhere'}),
])
def test_restricted_operations_have_no_side_effects(name,args):
    b=Backend(fixture(1)); start=b.snapshot()
    r=execute(b,'C001',name,args)
    assert not r['ok']; assert r['policy_violation']; assert b.snapshot()==start; b.close()


def test_wallet_debit_and_insufficient_balance():
    b=Backend(fixture(1,status='pending',paid=False,balance=2637))
    assert execute(b,'C001','pay_with_wallet',{'order_id':'O001'})['ok']
    assert b.snapshot()['customers'][0]['wallet_cents']==0
    assert b.snapshot()['wallet_transactions'][0]['amount_cents']==-2637
    assert not execute(b,'C001','pay_with_wallet',{'order_id':'O001'})['ok']; b.close()
    b=Backend(fixture(1,status='pending',paid=False,balance=2636)); before=b.snapshot()
    assert not execute(b,'C001','pay_with_wallet',{'order_id':'O001'})['ok']
    assert b.snapshot()==before; b.close()


@pytest.mark.parametrize('args',[{}, {'order_id':3},{'order_id':'O001','customer_id':'OTHER'},[],None,{'order_id':''}])
def test_schema_errors_are_safe(args):
    b=Backend(fixture(1)); before=b.snapshot()
    assert execute(b,'C001','get_order',args)['error']=='invalid_arguments'
    assert b.snapshot()==before; b.close()


def test_fresh_database_has_no_contamination():
    f=fixture(1,status='pending'); b=Backend(f)
    b.invoke('C001','cancel_order',{'order_id':'O001'}); b.close()
    b=Backend(f); assert b.snapshot()['orders'][0]['status']=='pending'; b.close()


def test_transaction_rolls_back_mid_refund_failure():
    f=fixture(1,status='cancelled')
    f['wallet_transactions']=[dict(transaction_id='existing',customer_id='C001',amount_cents=1,transaction_type='refund',reference_id='refund:O001')]
    b=Backend(f); before=b.snapshot()
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError): b.invoke('C001','process_refund',{'order_id':'O001'})
    assert b.snapshot()==before; b.close()
