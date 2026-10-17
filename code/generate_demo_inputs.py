"""Regenerate the exact fictional CSV inputs from a deterministic fixed seed.

Run from repository root: python code/generate_demo_inputs.py
No real customer, employer, or account information is used.
"""
from pathlib import Path
from dataclasses import asdict
import json
from evaluation import generate, dump_csv

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DATA.mkdir(parents=True,exist_ok=True)
for scenario in ('narrow_sufficient','uncertain_labels'):
    accounts, events, _oracle, config = generate(scenario, seed=20261015)
    dump_csv(accounts,DATA/f'{scenario}_accounts.csv')
    dump_csv(events,DATA/f'{scenario}_events.csv')
    (DATA/f'{scenario}_config.json').write_text(json.dumps(asdict(config),indent=2)+'\n',encoding='utf-8')
    print(f'{scenario}: {len(accounts):,} fictional attempts and {len(events):,} event records')
