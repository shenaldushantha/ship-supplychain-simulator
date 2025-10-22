import argparse, json, pandas as pd
from .data_loader import load_excel
from .simulate import run_once
from .kpis import compute_kpis
def parse_scenario(scen_df, name):
    rows = scen_df[scen_df['Scenario'] == name]
    if rows.empty: return {}
    d = {}
    for _,r in rows.iterrows():
        d[str(r['Param']).strip()] = str(r['Value']).strip()
    return d
def main():
    ap=argparse.ArgumentParser(description='Project Ship CLI')
    ap.add_argument('--data', default='data/sample_data.xlsx'); ap.add_argument('--scenario', default='base')
    ap.add_argument('--seed', type=int, default=42); args=ap.parse_args()
    data=load_excel(args.data); tasks=data['tasks']; scen=parse_scenario(data['scenarios'], args.scenario)
    finish, order, cp, tasks = run_once(tasks, seed=args.seed, scenario=scen)
    k = compute_kpis(tasks, finish); print('# Summary'); print(json.dumps(k, indent=2))
if __name__=='__main__': main()
