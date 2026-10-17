"""Correct derived verdicts uniformly while preserving every original record."""
import argparse
import copy
import csv
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from evaluation.runner import load_cases
from evaluation.assertions import evaluate


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rescore(source,output):
    source,output=Path(source),Path(output)
    cases={c['test_id']:c for c in load_cases('benchmark/tickets.jsonl')}
    changes=[]
    for origin in sorted(p for p in source.iterdir() if (p/'runs.jsonl').exists()):
        destination=output/origin.name; destination.mkdir(parents=True,exist_ok=True)
        if any(destination.iterdir()): raise ValueError(f'Refusing to overwrite existing derived records: {destination}')
        manifest=load_json(origin/'manifest.json')
        old_hashes=manifest['source_hashes']
        checker_key=next(k for k in old_hashes if k.replace('\\','/')=='evaluation/assertions.py')
        assert old_hashes[checker_key]==sha(source/'evaluation_assertions.original-v2.py')
        for path,digest in old_hashes.items():
            if path!=checker_key: assert sha(path)==digest,path
        assert sha(manifest['config']['benchmark'])==manifest['benchmark_hash']
        original_manifest_sha=sha(origin/'manifest.json')
        new=copy.deepcopy(manifest)
        new['record_stage']='audited_rescore_from_immutable_real_traces'
        new['execution_source_hashes']=old_hashes
        new['source_hashes'][checker_key]=sha('evaluation/assertions.py')
        new['rescored_at_utc']=datetime.now(timezone.utc).isoformat()
        new['parent_experiment']=Path(os.path.relpath(origin.resolve(),destination.resolve())).as_posix()
        new['parent_manifest_sha256']=original_manifest_sha
        new['original_checker_snapshot']=Path(os.path.relpath((source/'evaluation_assertions.original-v2.py').resolve(),destination.resolve())).as_posix()
        new['evaluation_revision']={'version':'checker-v3-target-context','reason':'Apply order-state facts to the requested order; accept error-status facts grounded in actual missing/ownership tool errors.',
            'original_checker_sha256':old_hashes[checker_key],'corrected_checker_sha256':sha('evaluation/assertions.py')}
        rows=[]
        for record in load_cases(origin/'runs.jsonl'):
            original_trace=origin/record['trace']; events=load_cases(original_trace)
            final=events[-1]; assert final['event']=='evaluation'
            calls=[e for e in events if e['event']=='tool']
            verdict=evaluate(cases[record['test_id']],final['final_state'],record['response'],calls,record['terminal'])
            revised={**record,**verdict,'original_passed':record['passed'],
                     'trace':Path(os.path.relpath(original_trace.resolve(),destination.resolve())).as_posix()}
            rows.append(revised)
            if any(record[k]!=verdict[k] for k in verdict):
                changes.append({'model':record['model_label'],'ticket':record['test_id'],
                    'original_passed':record['passed'],'corrected_passed':verdict['passed'],
                    'original_response_errors':record['response_errors'],'corrected_response_errors':verdict['response_errors']})
        (destination/'manifest.json').write_text(json.dumps(new,indent=2),encoding='utf-8')
        (destination/'runs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
        with (destination/'runs.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    log={'revision':'checker-v3-target-context','source':str(source),'changed_verdicts':changes,
         'raw_records_and_traces_modified':False,'additional_model_calls':0}
    (output/'rescore_audit.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
    print(json.dumps(log,indent=2)); return log


def load_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('--output',required=True)
    a=p.parse_args(); rescore(a.source,a.output)
