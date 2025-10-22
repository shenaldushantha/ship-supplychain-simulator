from typing import Dict, List
from .model import Task
class CycleError(Exception): pass
def topo_order(tasks: Dict[str, Task]) -> List[str]:
    indeg = {k:0 for k in tasks}
    for t in tasks.values():
        for d in t.depends_on:
            if d not in tasks: raise KeyError(f"Missing dependency {d} for {t.id}")
            indeg[t.id]+=1
    q=[k for k,v in indeg.items() if v==0]; order=[]
    while q:
        n=q.pop(0); order.append(n)
        for t in tasks.values():
            if n in t.depends_on:
                indeg[t.id]-=1
                if indeg[t.id]==0: q.append(t.id)
    if len(order)!=len(tasks): raise CycleError('cycle detected')
    return order
def forward_pass(tasks, order):
    for tid in order:
        t=tasks[tid]; t.es=0.0 if not t.depends_on else max(tasks[d].ef for d in t.depends_on); t.ef=t.es+t.duration
def backward_pass(tasks, order):
    project_finish=max(tasks[tid].ef for tid in order)
    for tid in reversed(order):
        t=tasks[tid]; succ=[o for o in tasks if tid in tasks[o].depends_on]
        t.lf=project_finish if not succ else min(tasks[s].ls for s in succ)
        t.ls=t.lf-t.duration; t.slack=round(t.ls-t.es,2)
    return project_finish
def critical_path(tasks): return [tid for tid,t in tasks.items() if abs(t.slack)<1e-6]
