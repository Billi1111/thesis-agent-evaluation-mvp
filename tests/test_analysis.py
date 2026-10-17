from analysis.analyze_results import summarize,paired_contrast


def row(case='T1',passed=True,terminal='completed',repeat=0):
    return dict(test_id=case,category='example',passed=passed,terminal=terminal,repeat=repeat,
        response_errors=[],missing_evidence=[],
        database_correct=passed,business_violations=[],latency_seconds=2,input_tokens=10,output_tokens=5,
        usage_complete=True,tool_calls=1,tool_errors=0,api_cost_usd=0,failure_categories=[] if passed else ['wrong_database_state'])


def test_infrastructure_is_separate_and_failures_keep_cost_latency():
    s=summarize([row(),row('T2',False),row('T3',False,'infrastructure_error')])
    assert s['attempts']==2 and s['infrastructure_failures']==1
    assert s['success_rate_pct']==50 and s['mean_latency_seconds']==2
    assert s['all_repeats_success_rate_pct'] is None


def test_paired_bootstrap_preserves_task_clusters():
    a=[row('T1',True,repeat=i) for i in range(2)]+[row('T2',False,repeat=i) for i in range(2)]
    b=[row('T1',True,repeat=i) for i in range(2)]+[row('T2',True,repeat=i) for i in range(2)]
    result=paired_contrast(a,b,resamples=100)
    assert result['paired_tasks']==2 and result['difference_percentage_points']==50
