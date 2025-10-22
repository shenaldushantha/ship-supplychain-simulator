import pandas as pd
from .model import Task
def load_excel(path: str):
    xls = pd.read_excel(path, sheet_name=None)
    tasks_df = xls['Tasks']
    suppliers_df = xls.get('Suppliers')
    scenarios_df = xls.get('Scenarios')
    tasks = []
    for _, row in tasks_df.iterrows():
        deps = []
        dep = row.get('DependsOn')
        if isinstance(dep, str) and dep.strip():
            deps = [d.strip() for d in dep.split(',')]
        tasks.append(Task(
            id=str(row['ID']).strip(),
            name=str(row['Name']).strip(),
            stage=str(row['Stage']).strip(),
            depends_on=deps,
            min_days=float(row['MinDays']),
            max_days=float(row['MaxDays']),
            fixed_days=float(row['FixedDays']) if pd.notna(row.get('FixedDays')) else None,
            resource=str(row.get('Resource','')),
            supplier=str(row.get('Supplier','')),
        ))
    return {'tasks': tasks, 'suppliers': suppliers_df, 'scenarios': scenarios_df}
