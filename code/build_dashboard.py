"""Generate a standalone, offline, English dashboard from synthetic observed inputs.

Do not use the generator's oracle or unassigned counterfactual outcomes.
"""
import json
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
from evaluation import Config, snapshot, validate, recommend


def metric_snapshot(x):
    out = {}
    for arm in ('retain', 'narrow', 'retire'):
        r = x.loc[x.arm == arm]
        n = len(r)
        tested = r.policy_declined.eq(1)
        audited = (r.legitimate_review.eq(1) | r.fraud_review.eq(1))
        known_fraud = r.fraud_review.eq(1)
        known_declined_fraud = (tested & known_fraud)
        fraud_n = known_fraud.sum()
        tested_n = tested.sum()
        # Precision and recall only receive an unqualified value with full independent-audit coverage.
        coverage = float(audited.mean())
        complete_audit = coverage >= 1.0 - 1e-9
        total_fraud_dollars = float(r.loc[known_fraud,'requested_amount'].sum())
        test_decline_dollars = float(r.loc[tested,'requested_amount'].sum())
        fraud_decline_dollars = float(r.loc[known_declined_fraud,'requested_amount'].sum())
        out[arm] = {
            'n': int(n),
            'decline_rate': float(tested.mean()),
            'unit_precision': (float(known_declined_fraud.sum() / tested_n) if tested_n and complete_audit else None),
            'unit_recall': (float(known_declined_fraud.sum() / fraud_n) if fraud_n and complete_audit else None),
            'dollar_precision': (float(fraud_decline_dollars / test_decline_dollars) if test_decline_dollars and complete_audit else None),
            'dollar_recall': (float(fraud_decline_dollars / total_fraud_dollars) if total_fraud_dollars and complete_audit else None),
            'audit_coverage': coverage,
            'policy_declines': int(tested_n),
            'bad_policy_declines': int(known_declined_fraud.sum()),
            'good_policy_declines': int((tested & r.legitimate_review.eq(1)).sum()) if complete_audit else None,
            'policy_blocked_requested_dollars': test_decline_dollars,
            'bad_policy_blocked_requested_dollars': fraud_decline_dollars if complete_audit else None,
            'good_policy_blocked_requested_dollars': (test_decline_dollars - fraud_decline_dollars) if complete_audit else None,
            'all_fraud_requested_dollars': total_fraud_dollars if complete_audit else None,
            'good_final_approved_requested_dollars': float(r.loc[(r.approved.eq(1) & r.legitimate_review.eq(1)),'requested_amount'].sum()) if complete_audit else None,
            'good_final_approved_dollars_per_eligible': float(r.loc[(r.approved.eq(1) & r.legitimate_review.eq(1)),'requested_amount'].sum() / n) if complete_audit else None,
            'average_blocked_requested_amount': float(test_decline_dollars / tested_n) if tested_n else None,
            'reviewed_fraud_intent': int(fraud_n),
            'fraud_policy_declines': int(known_declined_fraud.sum()),
            'requested_amount': float(r.requested_amount.sum()),
            'net_loss_per_eligible': float(r.net.mean()),
            'net_loss_bps_observed': float(r.net.sum() / r.requested_amount.sum() * 1e4),
            'known_legit_final_approval_rate': float((r.approved * r.legitimate_review).mean()),
            'final_approval_rate': float(r.approved.mean()),
            'financial_open_share': float(1-r.financial_horizon_closed.mean()),
            'unknown_intent_share': float(1-coverage),
            'pending_target_per_eligible': float(r.pending_target_classification.mean()),
        }
    return out


def load_data():
    data = {}
    for scenario, label in [('narrow_sufficient', 'Narrower rule sufficient'), ('uncertain_labels', 'Unresolved fraud outcomes')]:
        a = pd.read_csv(ROOT/f'data/{scenario}_accounts.csv')
        e = pd.read_csv(ROOT/f'data/{scenario}_events.csv')
        cfg = Config(**json.loads((ROOT/f'data/{scenario}_config.json').read_text()))
        validate(a,e,cfg)
        checkpoints = {}
        for day in (14,90):
            x = snapshot(a,e,day,cfg)
            arm_metrics = metric_snapshot(x)
            decision = recommend(x,cfg,'integrated')
            # Protective benefit is contrasted net-loss difference between independently randomized synthetic arms.
            # It is not derived causally from decline/precision/recall in isolation.
            benefit = {}
            for candidate in ('narrow','retire'):
                z = arm_metrics[candidate]; baseline = arm_metrics['retain']
                benefit[candidate] = {
                    'incremental_recognized_net_loss_per_eligible': z['net_loss_per_eligible'] - baseline['net_loss_per_eligible'],
                    'incremental_final_approval_rate': z['final_approval_rate'] - baseline['final_approval_rate'],
                    'incremental_supported_legit_approval_rate': z['known_legit_final_approval_rate']-baseline['known_legit_final_approval_rate'],
                    'loss_interval': decision['alternatives'].get(candidate,{}).get('loss'),
                    'access_interval': decision['alternatives'].get(candidate,{}).get('access'),
                    'consumer_cost_interval': decision['alternatives'].get(candidate,{}).get('consumer_cost'),
                    'evidence_status': decision['alternatives'].get(candidate,{}).get('status','unresolved'),
                }
            checkpoints[str(day)] = dict(day=day,arms=arm_metrics,benefit=benefit,decision=decision['decision'],why=decision['reason'])
        data[scenario] = dict(label=label,config={'loss_margin':cfg.loss_margin,'access_margin':cfg.access_margin,'min_cost_gain':cfg.min_cost_gain,'intervention_cost':cfg.intervention_cost,'denial_cost':cfg.denial_cost},checkpoints=checkpoints)
    return data


def build():
    data = load_data()
    template=(ROOT/'docs/dashboard_template.html').read_text(encoding='utf-8')
    html=template.replace('/* __BUNDLED_DATA__ */',json.dumps(data,allow_nan=False,separators=(',',':')))
    if html==template:
        raise RuntimeError('Dashboard data marker was absent')
    (ROOT/'docs/index.html').write_text(html,encoding='utf-8')
    (ROOT/'results/dashboard_metrics.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('Built docs/monitoring_reference.html (offline) and results/dashboard_metrics.json')
    for scenario in data:
        for day in ('14','90'):
            c=data[scenario]['checkpoints'][day]
            print(scenario,day,'decision',c['decision'],'retain', {k:round(c['arms']['retain'][k]*100,2) if c['arms']['retain'][k] is not None else None for k in ('decline_rate','unit_precision','unit_recall')})

if __name__=='__main__':build()
