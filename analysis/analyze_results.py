"""Regenerate metrics and figures exclusively from saved actual run records."""
import argparse
import csv
import json
import math
import statistics
from collections import Counter,defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def wilson(passed,n):
    if not n: return [None,None]
    z=1.95996398454; p=passed/n; denom=1+z*z/n
    centre=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return [100*(centre-half),100*(centre+half)]


def summarize(rows):
    infra=[r for r in rows if r['terminal']=='infrastructure_error']
    attempts=[r for r in rows if r['terminal']!='infrastructure_error']
    n=len(attempts); passed=sum(r['passed'] for r in attempts)
    latency=[r['latency_seconds'] for r in attempts]
    calls=sum(r['tool_calls'] for r in attempts)
    def avg_tokens(key):
        values=[r[key] for r in attempts if r[key] is not None and r['usage_complete']]
        return statistics.mean(values) if values else None
    repeated=defaultdict(list)
    for r in attempts: repeated[r['test_id']].append(r['passed'])
    repeat_counts={len(v) for v in repeated.values()}
    return {'recorded':len(rows),'attempts':n,'infrastructure_failures':len(infra),'passed':passed,
        'success_rate_pct':100*passed/n if n else None,'success_wilson_95_pct':wilson(passed,n),
        'database_correct_pct':100*sum(r['database_correct'] for r in attempts)/n if n else None,
        'response_correct_pct':100*sum(not r['response_errors'] for r in attempts)/n if n else None,
        'inspection_evidence_complete_pct':100*sum(not r['missing_evidence'] for r in attempts)/n if n else None,
        'state_and_response_correct_pct':100*sum(r['database_correct'] and not r['response_errors'] and r['terminal']=='completed' for r in attempts)/n if n else None,
        'policy_violation_attempts':sum(bool(r['business_violations']) for r in attempts),
        'business_rule_violations':sum(len(r['business_violations']) for r in attempts),
        'mean_latency_seconds':statistics.mean(latency) if latency else None,
        'median_latency_seconds':statistics.median(latency) if latency else None,
        'p95_latency_seconds':float(np.percentile(latency,95)) if latency else None,
        'mean_input_tokens':avg_tokens('input_tokens'),'mean_output_tokens':avg_tokens('output_tokens'),
        'observed_input_tokens':sum(r['input_tokens'] or 0 for r in rows),
        'observed_output_tokens':sum(r['output_tokens'] or 0 for r in rows),
        'incomplete_usage_attempts':sum(not r['usage_complete'] for r in rows),
        'fully_metered_attempts':sum(r['usage_complete'] and r['input_tokens'] is not None and r['output_tokens'] is not None for r in rows),
        'tool_calls':calls,'tool_errors':sum(r['tool_errors'] for r in attempts),
        'tool_error_rate_pct':100*sum(r['tool_errors'] for r in attempts)/calls if calls else 0,
        'total_api_cost_usd':sum(r['api_cost_usd'] for r in rows),
        'api_cost_per_success_usd':sum(r['api_cost_usd'] for r in rows)/passed if passed else None,
        'local_compute_cost_usd':None,
        'terminal_states':dict(Counter(r['terminal'] for r in rows)),
        'all_repeats_success_rate_pct':100*sum(all(v) for v in repeated.values())/len(repeated) if repeated and min(repeat_counts)>=2 and len(repeat_counts)==1 else None,
        'failures':dict(Counter(cat for r in attempts if not r['passed'] for cat in r['failure_categories'])),
        'category_success_pct':{cat:100*sum(r['passed'] for r in group)/len(group) for cat,group in group_by(attempts,'category').items()}}


def group_by(rows,key):
    groups=defaultdict(list)
    for row in rows: groups[row[key]].append(row)
    return groups


def paired_contrast(a,b,seed=42,resamples=10000):
    # Task-level paired cluster bootstrap: repetitions stay in their task cluster.
    ga,gb=group_by(a,'test_id'),group_by(b,'test_id')
    ids=sorted(set(ga)&set(gb))
    ids=[i for i in ids if {r['repeat'] for r in ga[i]}=={r['repeat'] for r in gb[i]} and not any(r['terminal']=='infrastructure_error' for r in ga[i]+gb[i])]
    if not ids: return None
    deltas=np.array([np.mean([r['passed'] for r in gb[i]])-np.mean([r['passed'] for r in ga[i]]) for i in ids])
    rng=np.random.default_rng(seed); boot=deltas[rng.integers(0,len(ids),size=(resamples,len(ids)))].mean(axis=1)*100
    return {'paired_tasks':len(ids),'difference_percentage_points':float(deltas.mean()*100),
        'paired_task_bootstrap_95_pp':np.percentile(boot,[2.5,97.5]).tolist(),'resamples':resamples,
        'interpretation':'Exploratory authored baseline, not confirmatory held-out thesis evidence.'}


def analyze(paths,output):
    records=[]; manifests=[]
    for p in map(Path,paths):
        manifest=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
        if manifest['kind']!='actual_local_model_inference': raise ValueError('Only real inference experiments may be analyzed')
        manifests.append(manifest)
        records.extend(json.loads(line) for line in (p/'runs.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())
    for key in ('benchmark_hash','harness_hash','tools_hash','source_hashes'):
        if any(m[key]!=manifests[0][key] for m in manifests): raise ValueError(f'Incomparable experiments: {key} differs')
    if any(m['config']['settings']!=manifests[0]['config']['settings'] for m in manifests): raise ValueError('Inference settings differ')
    keys=[(r['test_id'],r['model_label'],r['repeat']) for r in records]
    if len(set(keys))!=len(keys): raise ValueError('Duplicate attempts supplied; do not combine smoke tests with the full experiment')
    out=Path(output); out.mkdir(parents=True,exist_ok=True); plots=out/'plots'; plots.mkdir(exist_ok=True)
    grouped=group_by(records,'model_label'); summary={m:summarize(rows) for m,rows in grouped.items()}
    labels=list(summary); colors=['#2563eb','#ea580c','#16a34a']
    planned=sum(len(m['case_ids'])*len(m['model_labels'])*m['repeats'] for m in manifests)
    summary_doc={'kind':'actual_local_model_inference','planned_attempts':planned,'recorded_attempts':len(records),
        'complete':len(records)==planned and not any(r['terminal']=='infrastructure_error' for r in records),
        'evaluation_revisions':sorted({m.get('evaluation_revision',{}).get('version','original_recorded_checker') for m in manifests}),
        'record_stages':sorted({m.get('record_stage','original_model_execution') for m in manifests}),
        'models':summary,'uncertainty':'Wilson intervals are descriptive; paired comparisons resample task clusters. Single trials do not establish repeated reliability.','cost_basis':manifests[0]['config']['pricing']}
    if len(labels)==2: summary_doc['paired_contrast']={f'{labels[1]} minus {labels[0]}':paired_contrast(grouped[labels[0]],grouped[labels[1]])}
    (out/'metrics.json').write_text(json.dumps(summary_doc,indent=2),encoding='utf-8')
    with (out/'runs.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120})
    def save(fig,name):
        fig.tight_layout(); fig.savefig(plots/(name+'.png'),dpi=240,bbox_inches='tight'); fig.savefig(plots/(name+'.svg'),bbox_inches='tight'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4)); vals=[summary[m]['success_rate_pct'] or 0 for m in labels]
    intervals=[summary[m]['success_wilson_95_pct'] for m in labels]
    ax.bar(labels,vals,color=colors[:len(labels)])
    if all(v[0] is not None for v in intervals): ax.errorbar(labels,vals,yerr=[[v-i[0] for v,i in zip(vals,intervals)],[i[1]-v for v,i in zip(vals,intervals)]],fmt='none',color='#111827',capsize=5)
    ax.set(ylabel='Policy-compliant task success (%)',ylim=(0,105),title='Observed success (95% descriptive Wilson intervals)'); save(fig,'overall_success')
    categories=sorted({r['category'] for r in records}); fig,ax=plt.subplots(figsize=(11,4.8)); x=np.arange(len(categories)); width=.8/len(labels)
    for j,m in enumerate(labels): ax.bar(x+j*width,[summary[m]['category_success_pct'].get(c,0) for c in categories],width,label=m,color=colors[j])
    ax.set_xticks(x+width*(len(labels)-1)/2,[c.replace('_','\n') for c in categories]); ax.set(ylabel='Task success (%)',ylim=(0,110),title='Category success'); ax.legend(); save(fig,'category_success')
    for key,name,ylabel,title in [('mean_latency_seconds','latency','Seconds per task','Mean end-to-end task latency'),('total_api_cost_usd','api_cost','USD','API charges: local inference (compute cost unmeasured)')]:
        fig,ax=plt.subplots(figsize=(7,4)); values=[summary[m][key] or 0 for m in labels]; ax.bar(labels,values,color=colors[:len(labels)]); ax.set(ylabel=ylabel,title=title)
        if not any(values): ax.set_ylim(0,1); ax.text(.5,.5,'$0 API charges; electricity and hardware unmeasured',ha='center',transform=ax.transAxes)
        save(fig,name)
    fig,ax=plt.subplots(figsize=(7,4)); x=np.arange(len(labels)); width=.35
    for j,(key,name) in enumerate([('mean_input_tokens','Input'),('mean_output_tokens','Output')]):
        ax.bar(x+j*width,[summary[m][key] or 0 for m in labels],width,label=name)
    ax.set_xticks(x+width/2,labels); ax.set(ylabel='Reported tokens per metered attempt',title='Token usage (unavailable/partial usage excluded)'); ax.legend(); save(fig,'tokens')
    failure_types=sorted({k for s in summary.values() for k in s['failures']})
    fig,ax=plt.subplots(figsize=(11,5))
    if failure_types:
        x=np.arange(len(failure_types)); width=.8/len(labels)
        for j,m in enumerate(labels): ax.bar(x+j*width,[summary[m]['failures'].get(c,0) for c in failure_types],width,label=m,color=colors[j])
        ax.set_xticks(x+width*(len(labels)-1)/2,[t.replace('_','\n') for t in failure_types]); ax.legend()
    else: ax.text(.5,.5,'No observed task failures',ha='center',transform=ax.transAxes)
    ax.set(ylabel='Attempts (categories may overlap)',title='Failure categories; infrastructure errors reported separately'); save(fig,'failures')
    lines=['# Actual local baseline results','', 'This report is generated from immutable real model run records. It contains no scripted-model benchmark results.', '',
        f"Recorded {len(records)} of {planned} planned attempts. Complete planned run: {summary_doc['complete']}. A full baseline comparison requires 100 unique tickets per model.", '',
        f"Scoring revision: {', '.join(summary_doc['evaluation_revisions'])}. Record stage: {', '.join(summary_doc['record_stages'])}. Audited rescoring preserves original execution records and uses no additional model calls; see the parent rescore_audit.json for the exact changed verdicts.", '',
        '| Model | Attempts | Passed | Success | DB correct | Mean / median / p95 seconds | Mean input / output tokens | API USD |',
        '|---|---:|---:|---:|---:|---|---|---:|']
    for m,s in summary.items():
        def fmt(v): return 'unavailable' if v is None else f'{v:.2f}'
        lines.append(f"| {m} | {s['attempts']} | {s['passed']} | {fmt(s['success_rate_pct'])}% | {fmt(s['database_correct_pct'])}% | {fmt(s['mean_latency_seconds'])} / {fmt(s['median_latency_seconds'])} / {fmt(s['p95_latency_seconds'])} | {fmt(s['mean_input_tokens'])} / {fmt(s['mean_output_tokens'])} | {s['total_api_cost_usd']:.2f} |")
    if len(labels)>1:
        best_rate=max(summary[m]['success_rate_pct'] or 0 for m in labels)
        best=[m for m in labels if summary[m]['success_rate_pct']==best_rate]
        best_text=f"Highest observed success: **{best[0]}**." if len(best)==1 else f"Observed success is tied across **{', '.join(best)}**."
        lines+=['',best_text+' This is one authored-domain baseline, not evidence that parameter count causes higher capability.','']
    for m,s in summary.items():
        hard=sorted(s['category_success_pct'],key=s['category_success_pct'].get)
        category_text=', '.join(f"{c} ({s['category_success_pct'][c]:.1f}%)" for c in hard[:3])
        lines += [f"{m}: lowest observed category rates: {category_text}. Infrastructure failures: {s['infrastructure_failures']}; attempted policy violations: {s['business_rule_violations']}. Failure counts: {json.dumps(s['failures'])}.",
            f"Response correctness: {fmt(s['response_correct_pct'])}%; inspection-evidence completeness: {fmt(s['inspection_evidence_complete_pct'])}%; state plus response correctness: {fmt(s['state_and_response_correct_pct'])}%.",
            f"Fully metered attempts: {s['fully_metered_attempts']}/{s['recorded']}. Token means exclude partial or unavailable usage; observed token totals are lower bounds when usage is incomplete.",'']
    lines += ['## Observable failure examples','', '| Model / ticket | Observable defect | Raw trace |','|---|---|---|']
    for m in labels:
        selected=[]
        for kind in ('wrong_database_state','incorrect_response','business_rule_violation','invalid_model_output'):
            sample=next((r for r in grouped[m] if kind in r['failure_categories'] and r['test_id'] not in selected),None)
            if sample:
                selected.append(sample['test_id'])
                detail=json.dumps({'category':kind,'tables':sample['mismatched_tables'],'response_errors':sample['response_errors'],'policy_attempts':sample['business_violations']})
                lines.append(f"| {m} / {sample['test_id']} | `{detail}` | `{sample['trace']}` (inside that model's experiment) |")
    lines += ['']
    if 'paired_contrast' in summary_doc:
        lines += ['Paired comparison: `'+json.dumps(summary_doc['paired_contrast'])+'`','']
        contrast=next(iter(summary_doc['paired_contrast'].values()))
        if contrast:
            lo,hi=contrast['paired_task_bootstrap_95_pp']
            if lo<=0<=hi:
                lines += ['The exploratory paired interval includes zero, so this single run does not establish a directional success-rate difference.','']
    lines += ['## Interpretation and limitations','',
        'Local inference has zero API charges, so these runs cannot establish a monetary API-cost advantage. Hardware, electricity, and amortization were not measured; latency and token consumption remain useful resource comparisons.', '',
        'The two models use different architectures, quantization schemes, and their embedded chat templates. Both share the agent, system prompt, tool schemas, fixtures, evaluator, token cap, temperature and seed. A larger parameter count does not establish a stronger model.', '',
        'Native-format parser rejections are reported as model/protocol-format failures. They may involve model output and llama.cpp template/parser compatibility; these observations do not establish an intrinsic reasoning defect. Connection, authentication and other server outages are reported separately as infrastructure failures.', '',
        'Models run in sequential blocks on one GPU. Server load and warm-up time are excluded from per-task latency. Task latency includes all model calls, tools, and execution-loop checks; loading times are retained in runtime logs. GPU placement is automatically fitted and can differ by model.', '',
        'This 100-ticket baseline has no held-out optimizer/router splits and must not be reused as the thesis final test set. Templates within categories are related. Wilson intervals and task-cluster bootstrap differences are exploratory. One repeat cannot measure pass^5 reliability or statistical stability.', '',
        'Final answers must satisfy a structured JSON contract, which makes scoring executable but adds formatting difficulty. Requested facts and known extra factual claims are checked; the free-text message is not fully semantically verified. Failure labels describe observable defects, not audited causal diagnoses.', '',
        'The primary score includes factual evidence as well as state, response and policy checks. Equivalent read tools and authoritative state returned by successful mutations count as evidence; no redundant lookup or exact call sequence is required. Database correctness and state-plus-response correctness are also reported separately.', '',
        'Harness optimization, model routing, human diagnostic audit, and the thesis A/B/C/D experiment are deferred by the approved baseline scope. No claims about these research hypotheses are made.', '',
        'Next steps: audit accepted and failed traces, freeze an unseen 200-task split, repeat attempts, then implement and evaluate GEPA and offline routing with adaptation-cost accounting. For a local cost-aware router, first measure energy/hardware costs or predeclare a resource proxy: identical zero API charges are not informative routing cost labels.']
    (out/'results_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary_doc,indent=2))
    return summary_doc


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('experiments',nargs='+'); p.add_argument('--output',required=True)
    a=p.parse_args(); analyze(a.experiments,a.output)
