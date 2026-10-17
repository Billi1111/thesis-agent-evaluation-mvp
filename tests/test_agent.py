"""Scripted completions test the harness only; they are never experiment data."""
import json
from agent.tool_calling_agent import ToolCallingAgent
from benchmark.generate import build_cases
from environment.backend import Backend

SETTINGS={'max_steps':3,'max_tool_calls':2,'task_timeout_seconds':10,'call_timeout_seconds':5}


class ScriptedModel:
    def __init__(self,messages): self.messages=iter(messages)
    def complete(self,*args): return next(self.messages),{'input_tokens':1,'output_tokens':1}


def tool(name,args):
    return {'role':'assistant','content':None,'tool_calls':[{'id':'x','function':{'name':name,'arguments':args}}]}


def test_actual_tool_dispatch_and_final_response():
    c=build_cases()[0]; b=Backend(c['initial_state'])
    model=ScriptedModel([tool('get_order',json.dumps({'order_id':c['order_id']})),{'role':'assistant','content':'final'}])
    r=ToolCallingAgent(model,'test',SETTINGS).solve(b,c)
    assert r['terminal']=='completed'; assert r['calls'][0]['result']['data']['status']=='pending'; b.close()


def test_malformed_arguments_do_not_crash_or_mutate():
    c=build_cases()[0]; b=Backend(c['initial_state']); before=b.snapshot()
    model=ScriptedModel([tool('cancel_order','{bad'),{'role':'assistant','content':'final'}])
    r=ToolCallingAgent(model,'test',SETTINGS).solve(b,c)
    assert r['calls'][0]['result']['error']=='malformed_json'; assert b.snapshot()==before; b.close()


def test_tool_budget_and_timeout_are_bounded():
    c=build_cases()[0]; b=Backend(c['initial_state'])
    model=ScriptedModel([tool('get_customer','{}')]*3)
    r=ToolCallingAgent(model,'test',SETTINGS).solve(b,c)
    assert r['terminal']=='tool_budget'; assert len(r['calls'])==2; b.close()
    class TimeoutModel:
        def complete(self,*args): raise TimeoutError('test timeout')
    b=Backend(c['initial_state']); r=ToolCallingAgent(TimeoutModel(),'test',SETTINGS).solve(b,c)
    assert r['terminal']=='model_timeout'; b.close()


def test_server_reported_generation_format_error_is_not_connection_failure():
    c=build_cases()[0]; b=Backend(c['initial_state'])
    class InvalidFormatModel:
        def complete(self,*args): raise RuntimeError('The model produced output that does not match the expected peg-native format')
    result=ToolCallingAgent(InvalidFormatModel(),'test',SETTINGS).solve(b,c)
    assert result['terminal']=='invalid_model_output'; b.close()
