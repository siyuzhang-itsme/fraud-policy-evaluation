"""Build the reader-first, offline fraud-evidence feedback-loop demo.

Every displayed number comes from the included fictional observed account and event
ledgers, with the information-availability day respected. No simulation oracle,
future event or alternative treatment record is used as an outcome observation.
"""
from pathlib import Path
import json
import pandas as pd
from build_dashboard import load_data

ROOT=Path(__file__).resolve().parents[1]


def evidence_snapshot(a, e, day):
    available=e.loc[e.available_day<=day]
    totals={}
    for kind in ['legitimate_review','fraud_review','commercial_claim',
                 'submitted_claim','pending_target_classification',
                 'recognized_fraud_loss','recovery','financial_horizon_closed']:
        events=available.loc[available.kind==kind]
        totals[kind]={'records':int(len(events)),
                      'accounts':int(events.account_id.nunique()),
                      'amount':round(float(events.amount.sum()),2)}
    # A naive *proxy* defined for this demonstration; NOT a model training label.
    claim_like=available.loc[available.kind.isin(['submitted_claim','commercial_claim'])]
    totals['unfiltered_claim_proxy']={'accounts':int(claim_like.account_id.nunique())}
    byarm={}
    a2=a[['account_id','arm']]
    events=available.merge(a2,on='account_id',how='left',validate='many_to_one')
    for arm in ['retain','narrow','retire']:
        ss=events.loc[events.arm==arm]
        byarm[arm]={kind:{'count':int((ss.kind==kind).sum()),
                          'amount':round(float(ss.loc[ss.kind==kind,'amount'].sum()),2)}
                    for kind in ['submitted_claim','commercial_claim','pending_target_classification',
                                 'recognized_fraud_loss','recovery']}
    return {'records':len(a), 'totals':totals, 'by_arm':byarm}


def build():
    data=load_data()  # existing validated inputs and conservative evaluator
    for scenario in data:
        ac=pd.read_csv(ROOT/'data'/f'{scenario}_accounts.csv')
        ev=pd.read_csv(ROOT/'data'/f'{scenario}_events.csv')
        for day in (14,90):
            data[scenario]['checkpoints'][str(day)]['feedback']=evidence_snapshot(ac,ev,day)
    # Financial bridge: user-chosen illustrative interchange proxy, NEVER a
    # measured settlement / issuer-net-interchange amount. Differences across
    # independently randomized arms are normalized to RETAIN's arm size.
    interchange_rate=0.01
    for scenario, sc in data.items():
        sc['config']['assumed_interchange_rate']=interchange_rate
        for day, checkpoint in sc['checkpoints'].items():
            arms=checkpoint['arms']; retain=arms['retain']; n=retain['n']
            tested={}
            for alternative in ('narrow','retire'):
                candidate=arms[alternative]
                net_loss_difference=(candidate['net_loss_per_eligible']-retain['net_loss_per_eligible'])*n
                legit_dollar_difference=(candidate['good_final_approved_dollars_per_eligible']-retain['good_final_approved_dollars_per_eligible'])*n
                interchange_difference=legit_dollar_difference*interchange_rate
                tested[alternative]={
                    'reference_eligible_attempts':n,
                    'incremental_recognized_net_fraud_loss':round(net_loss_difference,2),
                    'incremental_legitimate_final_approved_requested_dollars':round(legit_dollar_difference,2),
                    'illustrative_interchange_change':round(interchange_difference,2),
                    'illustrative_net_financial_delta':round(round(interchange_difference,2)-round(net_loss_difference,2),2),
                    # A positive delta is favorable to alternative vs RETAIN.
                    # At day 14 or if ANY synthetic outcome remains open, not settled.
                    'can_treat_as_mature':(day=='90' and all(arms[k]['financial_open_share']<1e-9 for k in ('retain',alternative))),
                }
            checkpoint['dollar_impact']={
                'interchange_rate':interchange_rate,
                'retain_reference_eligible_attempts':n,
                'tested_alternatives':tested,
                'blocked_interchange_upper_bound':round(retain['good_policy_blocked_requested_dollars']*interchange_rate,2),
            }
        early=sc['checkpoints']['14']; late=sc['checkpoints']['90']
        sc['feedback_cycle']={
            'from_day':14,'to_day':90,
            'new_recognized_events':late['feedback']['totals']['recognized_fraud_loss']['records']-early['feedback']['totals']['recognized_fraud_loss']['records'],
            'new_recognized_dollars':round(late['feedback']['totals']['recognized_fraud_loss']['amount']-early['feedback']['totals']['recognized_fraud_loss']['amount'],2),
            'new_recovery_events':late['feedback']['totals']['recovery']['records']-early['feedback']['totals']['recovery']['records'],
            'new_recovery_dollars':round(late['feedback']['totals']['recovery']['amount']-early['feedback']['totals']['recovery']['amount'],2),
            'still_pending_target_labels':late['feedback']['totals']['pending_target_classification']['records'],
            'first_decision':early['decision'],'updated_decision':late['decision'],
        }
    template=(ROOT/'docs'/'feedback_loop_template.html').read_text(encoding='utf-8')
    marker='/* __BUNDLED_DATA__ */'
    if template.count(marker)!=1: raise RuntimeError('Expected one JSON marker')
    raw=json.dumps(data,allow_nan=False,separators=(',',':'))
    html=template.replace(marker,raw)
    (ROOT/'docs'/'index.html').write_text(html,encoding='utf-8')
    (ROOT/'results'/'feedback_loop_metrics.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('Built docs/index.html and results/feedback_loop_metrics.json')
    for case,sc in data.items():
        for day,dt in sc['checkpoints'].items():
            f=dt['feedback']['totals']
            print(case,'day',day,'decision',dt['decision'],
              'commercial',f['commercial_claim']['records'],
              'fraud claims',f['submitted_claim']['records'],
              'recognized',f['recognized_fraud_loss']['records'],
              'recoveries',f['recovery']['records'])
    return data
if __name__=='__main__': build()
