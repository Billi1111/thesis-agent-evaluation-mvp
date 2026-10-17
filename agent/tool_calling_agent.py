# Copyright Sierra (original loop); local adaptations copyright 2026 thesis authors.
# Derived from sierra-research/tau-bench, MIT, commit
# 59a200c6d575d595120f1cb70fea53cef0632f6b, tau_bench/agents/tool_calling_agent.py.
# See licenses/tau-bench-MIT.txt and upstream_tool_calling_agent.py.txt.
"""Adapted upstream message -> action -> observation execution loop.

Changes: injected real local model, scripted task input (no simulated user),
schema enforcement, sequential processing of all returned calls, resource limits,
incremental observable traces, and separate state evaluator. No code executor.
"""
import json
import socket
import time
from copy import deepcopy
from datetime import datetime, timezone
from openai import APITimeoutError
from agent.tools import TOOLS,execute


class ToolCallingAgent:
    def __init__(self, model, system_prompt, settings):
        self.model,self.system_prompt,self.settings=model,system_prompt,settings

    def solve(self, backend, case, emit=lambda event:None):
        start=time.perf_counter()
        messages=[{'role':'system','content':self.system_prompt},
                  {'role':'user','content':f"Authenticated customer: {case['customer_id']}\n"+case['user_request']}]
        calls,usage=[],[]
        terminal,final='step_limit',''
        emit({'event':'start','timestamp':datetime.now(timezone.utc).isoformat(),'messages':deepcopy(messages)})
        try:
            for step in range(1,self.settings['max_steps']+1):
                remaining=self.settings['task_timeout_seconds']-(time.perf_counter()-start)
                if remaining<=0:
                    terminal='model_timeout'; break
                emit({'event':'model_request','step':step})
                msg,counts=self.model.complete(messages,TOOLS,min(remaining,self.settings['call_timeout_seconds']))
                usage.append(counts)
                emit({'event':'model_response','step':step,'message':deepcopy(msg),'usage':counts})
                messages.append(msg)
                tool_calls=msg.get('tool_calls') or []
                if not tool_calls:
                    final=msg.get('content') or ''; terminal='completed'; break
                for tool_call in tool_calls:
                    if len(calls)>=self.settings['max_tool_calls']:
                        terminal='tool_budget'; break
                    if time.perf_counter()-start>=self.settings['task_timeout_seconds']:
                        terminal='model_timeout'; break
                    name=tool_call['function']['name']; raw=tool_call['function']['arguments']
                    try:
                        args=json.loads(raw)
                        result=execute(backend,case['customer_id'],name,args)
                    except (ValueError,TypeError):
                        args=raw; result={'ok':False,'error':'malformed_json','message':'Arguments must be a JSON object','policy_violation':False}
                    call={'step':len(calls)+1,'model_step':step,'name':name,'arguments':args,'result':result}
                    calls.append(call); emit({'event':'tool',**deepcopy(call)})
                    messages.append({'role':'tool','tool_call_id':tool_call['id'],'name':name,'content':json.dumps(result)})
                if terminal in ('tool_budget','model_timeout'): break
        except (TimeoutError,socket.timeout,APITimeoutError) as exc:
            terminal='model_timeout'; emit({'event':'error','type':terminal,'message':str(exc)})
        except Exception as exc:
            # llama.cpp reports its parser's rejection of generated output as HTTP 500.
            # This specific observable generation defect is not a connection failure.
            terminal='invalid_model_output' if 'model produced output that does not match the expected' in str(exc) else 'infrastructure_error'
            emit({'event':'error','type':type(exc).__name__,'terminal':terminal,'message':str(exc)})
        return {'terminal':terminal,'response':final,'calls':calls,'usage':usage,'messages':messages,
                'latency_seconds':time.perf_counter()-start}
