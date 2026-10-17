"""Real local inference adapters; no simulated backend is exposed in the CLI."""
import json
import time
from urllib.request import Request, urlopen


def request_json(url, data=None, timeout=10):
    req=Request(url, data=json.dumps(data).encode() if data is not None else None,
                headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=timeout) as r:
        return json.load(r)


class LocalModel:
    def __init__(self, config, settings):
        self.config,self.settings=config,settings

    def complete(self, messages, tools, timeout):
        c,s=self.config,self.settings
        if c['backend']=='ollama':
            native=[]
            for msg in messages:
                msg=dict(msg)
                if msg.get('tool_calls'):
                    msg['tool_calls']=[dict(function={'name':t['function']['name'],'arguments':json.loads(t['function']['arguments'])}) for t in msg['tool_calls']]
                msg.pop('tool_call_id',None)
                native.append(msg)
            body={'model':c['model'],'messages':native,'tools':tools,'stream':False,
                  'options':{'temperature':s['temperature'],'seed':s['seed'],'num_ctx':s['context_tokens'],'num_predict':s['max_output_tokens']},
                  'keep_alive':'15m'}
            if 'think' in c: body['think']=c['think']
            raw=request_json(c['base_url'].rstrip('/')+'/api/chat',body,timeout)
            msg=raw['message']; calls=msg.get('tool_calls') or []
            # Do not persist private thinking text; retain observable output and usage only.
            out={'role':'assistant','content':msg.get('content','')}
            if calls:
                out['tool_calls']=[{'id':f'call_{time.time_ns()}_{i}','type':'function','function':{'name':t['function']['name'],'arguments':json.dumps(t['function']['arguments'])}} for i,t in enumerate(calls)]
            return out, {'input_tokens':raw.get('prompt_eval_count'),'output_tokens':raw.get('eval_count'),
                         'cached_input_tokens':None,'server_duration_ns':raw.get('total_duration'),'load_duration_ns':raw.get('load_duration')}
        from openai import OpenAI
        client=OpenAI(base_url=c['base_url'],api_key=c.get('api_key','local'),timeout=timeout,max_retries=0)
        raw=client.chat.completions.create(model=c['model'],messages=messages,tools=tools,
            temperature=s['temperature'],max_tokens=s['max_output_tokens'],seed=s['seed'])
        msg=raw.choices[0].message.model_dump(exclude_none=True)
        # Exclude any vendor reasoning extension from saved traces.
        msg={k:v for k,v in msg.items() if k in ('role','content','tool_calls')}
        u=raw.usage
        return msg, {'input_tokens':u.prompt_tokens if u else None,'output_tokens':u.completion_tokens if u else None,
                     'cached_input_tokens':getattr(getattr(u,'prompt_tokens_details',None),'cached_tokens',None)}
