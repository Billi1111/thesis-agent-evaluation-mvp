"""Independent final-record integrity, isolation and accounting audit."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from environment.backend import canonical
from evaluation.assertions import evaluate
from evaluation.runner import load_cases


def audit(root,output):
    root=Path(root); cases={c['test_id']:c for c in load_cases('benchmark/tickets.jsonl')}
    manifests=[]; by_model={}; initial_hashes={}; seen=set(); violations=[]
    for directory in sorted(p for p in root.iterdir() if (p/'runs.jsonl').exists()):
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['kind']=='actual_local_model_inference'
        if manifest.get('record_stage')=='audited_rescore_from_immutable_real_traces':
            parent=directory/manifest['parent_experiment']
            assert hashlib.sha256((parent/'manifest.json').read_bytes()).hexdigest()==manifest['parent_manifest_sha256']
            assert hashlib.sha256((directory/manifest['original_checker_snapshot']).read_bytes()).hexdigest()==manifest['evaluation_revision']['original_checker_sha256']
            original=json.loads((parent/'manifest.json').read_text(encoding='utf-8'))
            assert original['source_hashes']==manifest['execution_source_hashes']
            for name,digest in original['source_hashes'].items():
                if name.replace('\\','/')!='evaluation/assertions.py': assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
        manifests.append(manifest); rows=load_cases(directory/'runs.jsonl')
        assert len(rows)==100 and {r['test_id'] for r in rows}==set(cases),directory
        assert all(r['terminal']!='infrastructure_error' for r in rows),directory
        for r in rows:
            key=(r['test_id'],r['model_label'],r['repeat']); assert key not in seen; seen.add(key)
            events=load_cases(directory/r['trace'])
            final=events[-1]; assert final['event']=='evaluation'
            initial,after=final['initial_state'],final['final_state']
            assert initial==cases[r['test_id']]['initial_state'],(key,'wrong_fixture')
            for value,name in [(initial,'initial_state_hash'),(after,'final_state_hash')]:
                assert hashlib.sha256(canonical(value).encode()).hexdigest()==r[name]
            initial_hashes.setdefault(r['test_id'],set()).add(r['initial_state_hash'])
            calls=[e for e in events if e['event']=='tool']
            verdict=evaluate(cases[r['test_id']],after,r['response'],calls,r['terminal'])
            for field in verdict: assert verdict[field]==r[field],(key,field)
            for customer in initial['customers']:
                cid=customer['customer_id']
                old_ledger=sum(t['amount_cents'] for t in initial['wallet_transactions'] if t['customer_id']==cid)
                new_ledger=sum(t['amount_cents'] for t in after['wallet_transactions'] if t['customer_id']==cid)
                current=next(c for c in after['customers'] if c['customer_id']==cid)
                if current['wallet_cents']-customer['wallet_cents']!=new_ledger-old_ledger:
                    violations.append([key,'wallet_ledger_conservation'])
                if cid!=cases[r['test_id']]['customer_id'] and current!=customer:
                    violations.append([key,'unrelated_customer_changed'])
            for order in initial['orders']:
                if order['order_id']!=cases[r['test_id']]['order_id']:
                    if next(o for o in after['orders'] if o['order_id']==order['order_id'])!=order:
                        violations.append([key,'unrelated_order_changed'])
            payments={p['order_id']:p for p in after['payments']}
            for refund in after['refunds']:
                payment=payments[refund['order_id']]
                if refund['amount_cents']!=payment['amount_cents'] or refund['destination']!=payment['method'] or payment['status']!='refunded':
                    violations.append([key,'refund_payment_consistency'])
        by_model[directory.name]={'records':len(rows),'unique_tickets':len({r['test_id'] for r in rows}),
                                 'terminal_states':dict(Counter(r['terminal'] for r in rows))}
    assert len(manifests)==2,'Expected two completed model directories'
    for name in ('source_hashes','benchmark_hash','harness_hash','tools_hash','config_hash'):
        assert manifests[0][name]==manifests[1][name],name
    assert all(len(values)==1 for values in initial_hashes.values()),'Model initial states differ'
    changed=[path for path,sha in manifests[0]['source_hashes'].items() if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha]
    assert not changed,changed
    assert not violations,violations
    report={'actual_model_attempts':len(seen),'models':by_model,'identical_initial_state_pairs':len(initial_hashes),
            'all_recorded_assessments_revalidated':True,'current_scoring_sources_match_manifest':True,
            'model_facing_sources_unchanged_since_execution':True,
            'wallet_ledger_refund_and_unrelated_entity_invariant_violations':violations,
            'note':'These independent accounting checks do not replace the full task/response/policy score.'}
    Path(output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2)); return report


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root'); p.add_argument('--output',required=True)
    a=p.parse_args(); audit(a.root,a.output)
