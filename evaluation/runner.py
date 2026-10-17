"""CLI: validate, discover, run. Raw traces are append-only during each run."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from agent.model import LocalModel,request_json
from agent.tool_calling_agent import ToolCallingAgent
from agent.tools import TOOLS
from environment.backend import Backend,canonical
from evaluation.assertions import evaluate,validate_dataset
from evaluation.model_config import load_config


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load_cases(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def discover(config):
    info={}
    for model in config['models']:
        base=model['base_url'].rstrip('/')
        if base not in info:
            endpoint='/api/tags' if model['backend']=='ollama' else '/models'
            info[base]=request_json(base+endpoint)
    return info


def run(config_path, output, limit=None, ids=None, repeats=1, labels=None, resume=False):
    config=load_config(config_path)
    cases=load_cases(config['benchmark']); validate_dataset(cases)
    if ids: cases=[c for c in cases if c['test_id'] in ids]
    if limit: cases=cases[:limit]
    if not cases: raise ValueError('No matching tickets')
    models=[m for m in config['models'] if not labels or m['label'] in labels]
    if not models: raise ValueError('No matching models')
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    manifest_path=out/'manifest.json'
    sources={str(p):digest(p.read_bytes()) for folder in ('agent','environment','benchmark','evaluation') for p in sorted(Path(folder).glob('*')) if p.suffix in ('.py','.txt','.sql','.jsonl')}
    manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'config':config,
        'config_hash':digest(canonical(config).encode()),'benchmark_hash':digest(Path(config['benchmark']).read_bytes()),
        'harness_hash':digest(Path(config['harness']).read_bytes()),'tools_hash':digest(canonical(TOOLS).encode()),
        'source_hashes':sources,'python':sys.version,'platform':platform.platform(),
        'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
        'case_ids':[c['test_id'] for c in cases],'model_labels':[m['label'] for m in models],
        'repeats':repeats,'kind':'actual_local_model_inference','selected_agent_commit':'59a200c6d575d595120f1cb70fea53cef0632f6b'}
    manifest['runtime']={m['label']:json.loads((Path('experiments/runtime')/(m['label']+'.json')).read_text(encoding='utf-8-sig'))
        for m in models if (Path('experiments/runtime')/(m['label']+'.json')).exists()}
    if manifest_path.exists():
        if not resume: raise ValueError('Output already contains a manifest; use a new directory or --resume')
        old=json.loads(manifest_path.read_text())
        for key in ('config_hash','benchmark_hash','harness_hash','tools_hash','source_hashes','case_ids','model_labels','repeats'):
            if old[key]!=manifest[key]: raise ValueError(f'Resume rejected: {key} changed')
    else:
        # Preflight before recording an experiment; unavailable servers are not 100 model failures.
        inventory=discover({'models':models})
        manifest['server_inventory']=inventory
        for m in models:
            data=inventory[m['base_url'].rstrip('/')]
            available=[x.get('name') for x in data.get('models',[])] if m['backend']=='ollama' else [x.get('id') for x in data.get('data',[])]
            if m['model'] not in available: raise ValueError(f"Model {m['model']} is not loaded/available: {available}")
        manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    records_path=out/'runs.jsonl'
    completed=set()
    if records_path.exists():
        completed={(r['test_id'],r['model_label'],r['repeat']) for r in load_cases(records_path)}
    prompt=Path(config['harness']).read_text(encoding='utf-8')
    # Interleave model order by task; concurrency fixed at one for local GPU memory.
    rng=random.Random(config['settings']['seed'])
    jobs=[]
    for repeat in range(repeats):
        ordered=list(cases); rng.shuffle(ordered)
        for case in ordered:
            order=list(models); rng.shuffle(order)
            jobs.extend((case,m,repeat) for m in order)
    for case,m,repeat in jobs:
        key=(case['test_id'],m['label'],repeat)
        if key in completed: continue
        name=f"{case['test_id']}_{m['label']}_{repeat}"
        trace_path=out/'traces'/f'{name}.jsonl'; trace_path.parent.mkdir(exist_ok=True)
        if trace_path.exists():
            # Preserve partial traces from interrupted attempts instead of overwriting them.
            trace_path=trace_path.with_name(name+f'_restart_{datetime.now().strftime("%Y%m%d%H%M%S")}.jsonl')
        backend=Backend(case['initial_state'])
        initial=backend.snapshot()
        with trace_path.open('x',encoding='utf-8') as trace:
            def emit(event):
                trace.write(json.dumps(event,ensure_ascii=False)+'\n'); trace.flush()
            result=ToolCallingAgent(LocalModel(m,config['settings']),prompt,config['settings']).solve(backend,case,emit)
            final=backend.snapshot()
            assessment=evaluate(case,final,result['response'],result['calls'],result['terminal'])
            emit({'event':'evaluation','initial_state':initial,'final_state':final,'assessment':assessment})
        backend.close()
        usage=result['usage']
        def tokens(k):
            return sum(u[k] for u in usage) if usage and all(u.get(k) is not None for u in usage) else None
        record={**assessment,'test_id':case['test_id'],'category':case['category'],'difficulty':case['difficulty'],
            'model_label':m['label'],'model_id':m['model'],'repeat':repeat,'terminal':result['terminal'],
            'latency_seconds':result['latency_seconds'],'input_tokens':tokens('input_tokens'),'output_tokens':tokens('output_tokens'),
            'usage_complete':result['terminal'] not in ('model_timeout','infrastructure_error','invalid_model_output'),
            'api_cost_usd':0.0,'local_compute_cost_usd':None,'tool_calls':len(result['calls']),
            'tool_errors':sum(not c['result']['ok'] for c in result['calls']),
            'trace':str(trace_path.relative_to(out)),'initial_state_hash':digest(canonical(initial).encode()),
            'final_state_hash':digest(canonical(final).encode()),'response':result['response']}
        with records_path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(record,ensure_ascii=False)+'\n'); f.flush()
        print(f"{name}: {'PASS' if record['passed'] else 'FAIL'} {record['terminal']} {record['latency_seconds']:.1f}s",flush=True)
        if record['terminal']=='infrastructure_error':
            print('Stopping after infrastructure failure; inspect trace and resume after correction.',flush=True)
            break
    if records_path.exists():
        records=load_cases(records_path)
        with (out/'runs.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    else:
        records=[]
    expected_keys={(case['test_id'],m['label'],repeat) for case,m,repeat in jobs}
    actual_keys={(r['test_id'],r['model_label'],r['repeat']) for r in records}
    if not expected_keys <= actual_keys or any(r['terminal']=='infrastructure_error' for r in records):
        raise RuntimeError('Experiment is incomplete or contains infrastructure failures; inspect saved traces.')
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate'); v.add_argument('--benchmark',default='benchmark/tickets.jsonl')
    d=sub.add_parser('discover'); d.add_argument('--config',default='experiments/configs/llamacpp.json')
    r=sub.add_parser('run'); r.add_argument('--config',default='experiments/configs/llamacpp.json'); r.add_argument('--output',required=True)
    r.add_argument('--limit',type=int); r.add_argument('--ids',nargs='+'); r.add_argument('--models',nargs='+'); r.add_argument('--repeats',type=int,default=1); r.add_argument('--resume',action='store_true')
    args=p.parse_args()
    if args.command=='validate': print(json.dumps(validate_dataset(load_cases(args.benchmark)),indent=2))
    elif args.command=='discover': print(json.dumps(discover(load_config(args.config)),indent=2))
    else:
        if args.repeats<1 or (args.limit is not None and args.limit<1): p.error('Repetitions and limit must be positive')
        run(args.config,args.output,args.limit,args.ids,args.repeats,args.models,args.resume)


if __name__=='__main__': main()
