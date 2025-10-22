def compute_kpis(tasks, project_finish: float):
    stages={}
    for t in tasks.values():
        s=stages.setdefault(t.stage,{'start':t.es,'finish':t.ef})
        s['start']=min(s['start'], t.es); s['finish']=max(s['finish'], t.ef)
    return {
        'total_lead_time_days': round(project_finish,2),
        'stages': {k: round(v['finish']-v['start'],2) for k,v in stages.items()},
        'critical_tasks': [tid for tid,t in tasks.items() if abs(t.slack)<1e-6]
    }
