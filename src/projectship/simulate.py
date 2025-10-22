import random
from .model import Task
from .schedule import topo_order, forward_pass, backward_pass, critical_path
def apply_scenario(tasks, scenario):
    if scenario.get('DELAY_DAYS'):
        dd=float(scenario['DELAY_DAYS'])
        for t in tasks.values():
            if t.supplier: t.duration+=dd
    rate=float(scenario.get('DEFECT_RATE',0) or 0)
    if rate>0:
        low=float(scenario.get('REWORK_MIN',1)); high=float(scenario.get('REWORK_MAX',3))
        for t in tasks.values():
            if random.random()<rate: t.duration+=random.uniform(low, high)
def run_once(tasks_list, seed=None, scenario=None):
    rng=random.Random(seed); tasks={t.id:Task(**{**t.__dict__}) for t in tasks_list}
    for t in tasks.values(): t.set_duration(rng)
    if scenario: apply_scenario(tasks, scenario)
    order=topo_order(tasks); forward_pass(tasks, order); finish=backward_pass(tasks, order)
    cp=critical_path(tasks); return finish, order, cp, tasks
