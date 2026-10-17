"""Synthetic rule review. AI-assisted development prototype; professional review pending.

One independent account, one index attempt; fixed-horizon, three randomized arms.
Evaluator receives observed records only. Oracle is confined to simulation diagnostics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd

ARMS = ('retain', 'narrow', 'retire')

@dataclass(frozen=True)
class Config:
    n: int = 90000
    loss_margin: float = 0.35  # fictional dollars per enrolled account
    intervention_cost: float = 0.5
    denial_cost: float = 10.0
    min_cost_gain: float = 0.02
    access_margin: float = 0.002
    alpha: float = 0.05
    randomized: bool = True
    inference: str = 'bernstein'
    max_amount: float = 200.0  # prespecified support, never estimated from observed maxima
    # Fraction of still-unreported approved exposure allowed to become target loss.
    # 1 is assumption-light; smaller values require external justification.
    unreported_cap: float = 1.0

SCENARIOS = {
    'protective': dict(p=(.25,.20,.005), recovery=(.10,.10,.10)),
    'narrow_sufficient': dict(p=(.23,.055,.0045), segment_mix=(.008,.012,.98), recovery=(.30,.30,.30)),
    'retire_redundant': dict(p=(.004,.002,.001), recovery=(.30,.30,.30)),
    'recovery_reversal': dict(p=(.18,.04,.002), recovery=(.10,.95,.10)),
    'uncertain_labels': dict(p=(.23,.055,.0045), segment_mix=(.008,.012,.98), recovery=(.30,.30,.30), uncertain=.75),
    'delayed_outcomes': dict(p=(.25,.004,.002), recovery=(.30,.30,.30), delay=True),
    'clean_no_increment': dict(p=(.25,.004,.002), recovery=(.30,.30,.30)),
    'downstream_overlap': dict(p=(.004,.002,.001), recovery=(.30,.30,.30), overlap=True),
    'no_overlap': dict(p=(.25,.004,.002), recovery=(.30,.30,.30), no_overlap=True),
    'small_sample': dict(p=(.25,.004,.002), recovery=(.30,.30,.30), small=True),
    'unreported_tail': dict(p=(.25,.004,.002), recovery=(.30,.30,.30), tail=.02),
    'incomplete_legitimate_review': dict(p=(.25,.004,.002), recovery=(.30,.30,.30), review=.25),
}

def generate(scenario, seed=20261015, cfg=None):
    """IID synthetic accounts with latent preassignment behavior and potential outcomes.

    No employer parameters. Random arm independent of segment, intent and amount.
    Potential outcomes share baseline state but have only ONE observed arm each.
    Segments are prespecified: high-risk targeted by both policies, marginal only
    by retain, outside neither. Downstream checks are retained in all arms.
    """
    spec = SCENARIOS[scenario]
    cfg = cfg or Config()
    if scenario in ('narrow_sufficient','uncertain_labels'):
        cfg = replace(cfg,loss_margin=0.55,min_cost_gain=0.004)
    if spec.get('small'): cfg = replace(cfg, n=180)
    if spec.get('no_overlap'): cfg = replace(cfg, randomized=False)
    if spec.get('overlap'): cfg = replace(cfg, intervention_cost=0)
    rng = np.random.default_rng(seed)
    n = cfg.n
    segment = rng.choice(3,n,p=spec.get('segment_mix',(.10,.25,.65)))
    amount = rng.choice([50.,100.,200.],n,p=[.3,.5,.2])
    fraud = rng.random(n) < np.array(spec['p'])[segment]
    downstream = rng.random(n) < .10
    if spec.get('overlap'): downstream |= (segment != 2)
    recovery_fraction = np.array(spec['recovery'])[segment]
    latent_net = amount * fraud * (1-recovery_fraction)
    blocked = np.array([segment!=2,segment==0,np.zeros(n,dtype=bool)])
    approved = ~blocked & ~downstream
    pot_loss = approved * latent_net
    pot_access = approved * ~fraud
    pot_cost = ~fraud * (cfg.intervention_cost*blocked + cfg.denial_cost*~approved)
    armidx = rng.integers(0,3,n)
    if spec.get('no_overlap'): armidx[:] = 0
    idx = np.arange(n)
    chosen_approved = approved[armidx,idx]
    a = pd.DataFrame(dict(account_id=idx, arm=np.array(ARMS)[armidx],
        segment=segment, requested_amount=amount, policy_declined=blocked[armidx,idx].astype(int),
        downstream_declined=((~blocked[armidx,idx])&downstream).astype(int),
        approved=chosen_approved.astype(int), assignment_probability=np.full(n,1/3 if cfg.randomized else 1.)))
    events=[]
    def emit(mask,kind,day,values=0, lag=0):
        ids=np.flatnonzero(mask)
        vals=np.broadcast_to(values,(n,))
        days=np.broadcast_to(day,(n,))
        for i in ids:
            events.append((len(events),int(i),kind,int(days[i]),int(days[i]+lag),float(vals[i])))
    # Supported legitimate / fraud intent review is a separate synthetic audit.
    # Complete audit is intentionally an idealization. Missing review gets bounds.
    reviewed = rng.random(n) >= spec.get('review',0)
    emit(reviewed&~fraud,'legitimate_review',7)
    emit(reviewed&fraud,'fraud_review',7)
    # Commercial disputes are not financial fraud-loss events.
    emit(chosen_approved&~fraud&(rng.random(n)<.015),'commercial_claim',10,amount)
    claim = chosen_approved & fraud
    uncertain = claim & (rng.random(n)<spec.get('uncertain',0))
    tail = chosen_approved & (rng.random(n)<spec.get('tail',0))
    recognition_day = np.full(n,21)
    if spec.get('delay'):
        recognition_day=np.where(armidx==0,10,65)
    emit(claim,'submitted_claim',10,amount)
    emit(uncertain,'pending_target_classification',12,amount)
    emit(claim&~uncertain,'recognized_fraud_loss',recognition_day,amount,lag=2)
    emit(claim&~uncertain,'recovery',75,amount*recovery_fraction)
    # Horizon closure means no additional recognized target loss THROUGH day 90.
    # It does not establish that the payment was legitimate or lifetime mature.
    emit(chosen_approved&~uncertain&~tail,'financial_horizon_closed',90)
    emit(~chosen_approved,'financial_horizon_closed',1)
    e=pd.DataFrame(events,columns=['event_id','account_id','kind','event_day','available_day','amount'])
    # Exact superpopulation estimands under the visible DGP; not arm observations.
    weights=np.array(spec.get('segment_mix',(.10,.25,.65))); pp=np.array(spec['p']); mean_amount=105.
    pass_downstream=np.array([0.,0.,.9]) if spec.get('overlap') else np.full(3,.9)
    block_seg=np.array([[1,1,0],[1,0,0],[0,0,0]],dtype=bool)
    oracle={k:{} for k in ('loss','access','consumer_cost')}
    for j,arm in enumerate(ARMS):
        ap=(1-block_seg[j])*pass_downstream
        oracle['loss'][arm]=float(np.sum(weights*ap*pp*mean_amount*(1-np.array(spec['recovery']))))
        oracle['access'][arm]=float(np.sum(weights*ap*(1-pp)))
        oracle['consumer_cost'][arm]=float(np.sum(weights*(1-pp)*(cfg.intervention_cost*block_seg[j]+cfg.denial_cost*(1-ap))))
    return a,e,oracle,cfg

def validate(a,e,cfg):
    if a.account_id.duplicated().any() or e.event_id.duplicated().any():
        raise ValueError('Duplicate account or event ID')
    if not set(a.arm)<=set(ARMS) or (a.requested_amount<=0).any() or (a.requested_amount>cfg.max_amount).any():
        raise ValueError('Invalid arm or exposure')
    if not set(e.account_id)<=set(a.account_id): raise ValueError('Unlinked event')
    kinds={'legitimate_review','fraud_review','commercial_claim','submitted_claim',
           'pending_target_classification','recognized_fraud_loss','recovery','financial_horizon_closed'}
    if not set(e.kind)<=kinds: raise ValueError('Unknown event type')
    if (e.amount<0).any() or (e.event_day<0).any() or (e.available_day<e.event_day).any():
        raise ValueError('Invalid amount or information time')
    for c in ['approved','policy_declined','downstream_declined']:
        if not set(a[c])<={0,1}: raise ValueError('Nonbinary treatment')
    if not ((a.approved+a.policy_declined+a.downstream_declined)==1).all():
        raise ValueError('Conflicting final handling')
    if not ((a.assignment_probability>0)&(a.assignment_probability<=1)).all():
        raise ValueError('Invalid assignment probability')
    if cfg.randomized and not np.allclose(a.assignment_probability,1/3):
        raise ValueError('Only equal probability three-arm randomization is implemented')
    money=e[e.kind.isin(['recognized_fraud_loss','recovery','submitted_claim','pending_target_classification'])]
    if not money.empty and not a.set_index('account_id').loc[money.account_id,'approved'].all():
        raise ValueError('Financial event on declined attempt')
    # Validate every availability prefix, not just full-history totals.
    ids=a.account_id.to_numpy()
    exposure=a.set_index('account_id').requested_amount
    for day in sorted(e.available_day.unique()):
        s=e[e.available_day<=day]
        def total(kind): return s[s.kind==kind].groupby('account_id').amount.sum().reindex(ids,fill_value=0).to_numpy()
        gross,rec,pending=total('recognized_fraud_loss'),total('recovery'),total('pending_target_classification')
        if np.any(rec>gross+1e-8) or np.any(gross+pending>exposure.loc[ids].to_numpy()+1e-8):
            raise ValueError('Invalid linked accounting prefix')
        legit=set(s[s.kind=='legitimate_review'].account_id)
        fraud=set(s[s.kind=='fraud_review'].account_id)
        if legit&fraud: raise ValueError('Contradictory intent evidence requires correction event support')
    if cfg.n!=len(a): raise ValueError('Config and cohort size differ')
    if not 0<cfg.alpha<1 or not 0<=cfg.unreported_cap<=1 or cfg.inference not in ('bernstein','normal'):
        raise ValueError('Invalid inference settings')
    if min(cfg.intervention_cost,cfg.denial_cost,cfg.min_cost_gain,cfg.access_margin,cfg.loss_margin)<0:
        raise ValueError('Negative decision setting')

def snapshot(a,e,day,cfg):
    """No latent intent, future events, or unchosen potential outcomes accepted."""
    if day<0: raise ValueError('Negative cutoff')
    s=e[e.available_day<=day]
    x=a.copy().set_index('account_id')
    for kind in ['recognized_fraud_loss','recovery','pending_target_classification','submitted_claim','commercial_claim']:
        x[kind]=s[s.kind==kind].groupby('account_id').amount.sum().reindex(x.index,fill_value=0)
    for kind in ['financial_horizon_closed','legitimate_review','fraud_review']:
        x[kind]=x.index.isin(s[s.kind==kind].account_id).astype(int)
    x['net']=x.recognized_fraud_loss-x.recovery
    # Recovery lower endpoint allows all remaining confirmed loss to be recovered
    # when the financial horizon is not closed; upper never assumes future recovery.
    x['loss_lo']=np.where(x.financial_horizon_closed,x.net,0)
    known=x.recognized_fraud_loss+x.pending_target_classification
    unseen=np.maximum(0,x.requested_amount-known)*x.approved*(1-x.financial_horizon_closed)
    x['loss_hi']=x.net+x.pending_target_classification+cfg.unreported_cap*unseen
    x['access_lo']=x.approved*x.legitimate_review
    x['access_hi']=x.approved*(1-x.fraud_review)
    burden=cfg.intervention_cost*x.policy_declined+cfg.denial_cost*(1-x.approved)
    x['cost_lo']=burden*x.legitimate_review
    x['cost_hi']=burden*(1-x.fraud_review)
    x['gross']=x.recognized_fraud_loss
    x['claims']=x.submitted_claim+x.commercial_claim
    return x.reset_index()

def interval(v,w,alpha,m):
    """Independent-account normal approximation, heterogeneous arm variances.

    Bonferroni adjusts the nominal marginal error budget only. It cannot repair
    a poor normal approximation, nonrandom assignment, or violated bounds.
    """
    delta=float(v.mean()-w.mean())
    se=float(np.sqrt(v.var(ddof=1)/len(v)+w.var(ddof=1)/len(w)))
    z=NormalDist().inv_cdf(1-alpha/(2*m))
    return delta-z*se,delta+z*se

def bounds(x,arm,lo,hi,cfg,m=12):
    c=x[x.arm==arm]; b=x[x.arm=='retain']
    if cfg.inference=='bernstein':
        # 18 arm-endpoint means, two tails each: delta=alpha/36 per one-sided
        # application of Maurer & Pontil (2009), Theorem 4, plus union bound.
        # Loss support is fixed BEFORE data, not the sample maximum.
        support=cfg.max_amount if lo.startswith('loss') else (1. if lo.startswith('access') else cfg.intervention_cost+cfg.denial_cost)
        def mean_interval(v):
            n=len(v); log=np.log(72/cfg.alpha)
            radius=np.sqrt(2*v.var(ddof=1)*log/n)+7*support*log/(3*(n-1))
            return max(0,float(v.mean()-radius)),min(support,float(v.mean()+radius))
        cl,ch=mean_interval(c[lo]),mean_interval(c[hi])
        bl,bh=mean_interval(b[lo]),mean_interval(b[hi])
        return [cl[0]-bh[1],ch[1]-bl[0]]
    lower=interval(c[lo].to_numpy(),b[hi].to_numpy(),cfg.alpha,m)[0]
    upper=interval(c[hi].to_numpy(),b[lo].to_numpy(),cfg.alpha,m)[1]
    return [float(lower),float(upper)]

def recommend(x,cfg,mode='integrated'):
    """Recommend a supported change; defer when unresolved options remain.

    Default: eighteen arm-endpoint means with two tails, union error alpha.
    Normal sensitivity: twelve two-sided endpoint-contrast intervals.
    Neither has a repeated-monitoring guarantee.
    For the strong baseline, exact observed net and supported access/cost are
    treated as complete. This is reasonable only after adequate reconciliation.
    """
    counts=x.groupby('arm').size()
    if len(counts)<3 or min(counts)<30 or not cfg.randomized:
        return dict(decision='defer',reason='Identification or sample-size gate',alternatives={})
    if mode in ('gross_point','claims_point'):
        key='gross' if mode=='gross_point' else 'claims'
        means=x.groupby('arm')[key].mean()
        for arm in ('retire','narrow'):
            if means[arm]-means['retain']<=cfg.loss_margin:
                return dict(decision=arm,reason='Point loss comparison only',alternatives={})
        return dict(decision='retain',reason='Point loss comparison only',alternatives={})
    if mode=='strong_conventional':
        x=x.copy()
        x['loss_lo']=x['loss_hi']=x.net
        x['access_hi']=x.access_lo
        x['cost_hi']=x.cost_lo
    alternatives={}
    for arm in ('narrow','retire'):
        loss=bounds(x,arm,'loss_lo','loss_hi',cfg)
        access=bounds(x,arm,'access_lo','access_hi',cfg)
        cost=bounds(x,arm,'cost_lo','cost_hi',cfg)
        feasible=loss[1]<=cfg.loss_margin and access[0]>=-cfg.access_margin and cost[1]<=-cfg.min_cost_gain
        rejected=loss[0]>cfg.loss_margin or access[1]<-cfg.access_margin or cost[0]>-cfg.min_cost_gain
        alternatives[arm]=dict(loss=loss,access=access,consumer_cost=cost,
            status='supported' if feasible else ('rejected' if rejected else 'unresolved'))
    for arm in ('retire','narrow'):
        if alternatives[arm]['status']=='supported':
            return dict(decision=arm,reason='At least this change is supported; inspect other option separately',alternatives=alternatives)
    decision='retain' if all(v['status']=='rejected' for v in alternatives.values()) else 'defer'
    return dict(decision=decision,reason='All alternatives rejected' if decision=='retain' else 'Evidence does not resolve a safe useful change',alternatives=alternatives)

def analyze(a,e,cfg,day=90,validate_input=True):
    if validate_input: validate(a,e,cfg)
    x=snapshot(a,e,day,cfg)
    decisions={m:recommend(x,cfg,m) for m in ('claims_point','gross_point','strong_conventional','integrated')}
    metrics=[]
    for arm,r in x.groupby('arm'):
        metrics.append(dict(arm=arm,n=len(r),requested_amount=float(r.requested_amount.sum()),
            net_per_account=float(r.net.mean()),net_bps=float(r.net.sum()/r.requested_amount.sum()*1e4),
            gross_per_account=float(r.gross.mean()),policy_decline_rate=float(r.policy_declined.mean()),
            final_approval_rate=float(r.approved.mean()),supported_legitimate_approved_per_account=float(r.access_lo.mean()),
            supported_cost_per_account=float(r.cost_lo.mean()),open_financial_fraction=float(1-r.financial_horizon_closed.mean()),
            unknown_intent_fraction=float(1-(r.legitimate_review+r.fraud_review).mean()),
            pending_per_account=float(r.pending_target_classification.mean())))
    return dict(day=day,decisions=decisions,metrics=metrics)

def oracle_decision(o,cfg):
    for arm in ('retire','narrow'):
        if o['loss'][arm]-o['loss']['retain']<=cfg.loss_margin and o['access'][arm]-o['access']['retain']>=-cfg.access_margin and o['consumer_cost'][arm]-o['consumer_cost']['retain']<=-cfg.min_cost_gain:
            return arm
    return 'retain'

def dump_csv(frame,path): frame.to_csv(path,index=False,float_format='%.10g')

def run(out,replications=60):
    out=Path(out); data=out/'data'; results=out/'results'
    data.mkdir(parents=True,exist_ok=True); results.mkdir(exist_ok=True)
    records=[]; summary=[]; metrics=[]; sensitivity=[]; mc=[]
    for sc in SCENARIOS:
        a,e,o,cfg=generate(sc)
        dump_csv(a,data/f'{sc}_accounts.csv'); dump_csv(e,data/f'{sc}_events.csv')
        (data/f'{sc}_config.json').write_text(json.dumps(asdict(cfg),indent=2)+'\n')
        # Separate diagnostic file; production evaluator has no oracle parameter.
        (data/f'{sc}_oracle_DIAGNOSTIC_ONLY.json').write_text(json.dumps(o,indent=2)+'\n')
        for day in (14,90):
            r=analyze(a,e,cfg,day,validate_input=(day==14)); r['scenario']=sc; records.append(r)
            summary.append(dict(scenario=sc,day=day,**{k:v['decision'] for k,v in r['decisions'].items()},oracle_full_cohort=oracle_decision(o,cfg)))
            metrics.extend(dict(scenario=sc,day=day,**v) for v in r['metrics'])
        # One-factor sweeps; never choose a favorable setting retrospectively.
        for param,values in [('loss_margin',[0,.10,.35,.75,2.]),('unreported_cap',[0,.01,.1,1.]),
                             ('denial_cost',[0,2,10,25]),('intervention_cost',[0,.5,2]),
                             ('alpha',[.01,.05,.10]),('min_cost_gain',[0,.02,.10]),('inference',['normal','bernstein'])]:
            for value in values:
                alt=replace(cfg,**{param:value})
                d=analyze(a,e,alt,90,validate_input=False)['decisions']['integrated']
                sensitivity.append(dict(scenario=sc,parameter=param,value=value,decision=d['decision']))
        # Fixed DGP grid, not selected for success; calibration is diagnostic only.
        for rep in range(replications):
            aa,ee,oo,cc=generate(sc,seed=100000+rep)
            r=analyze(aa,ee,cc,90,validate_input=False)
            target=oracle_decision(oo,cc)
            for method in ('gross_point','strong_conventional','integrated'):
                d=r['decisions'][method]; dec=d['decision']
                unsafe=False
                if dec in ('narrow','retire'):
                    unsafe=(oo['loss'][dec]-oo['loss']['retain']>cc.loss_margin or
                            oo['access'][dec]-oo['access']['retain']<-cc.access_margin or
                            oo['consumer_cost'][dec]-oo['consumer_cost']['retain']>-cc.min_cost_gain)
                # Coverage against exact superpopulation contrasts from the DGP.
                covered=True
                for arm,v in d['alternatives'].items():
                    for key,okey in [('loss','loss'),('access','access'),('consumer_cost','consumer_cost')]:
                        truth=oo[okey][arm]-oo[okey]['retain']
                        covered &= v[key][0]<=truth<=v[key][1]
                mc.append(dict(scenario=sc,rep=rep,method=method,decision=dec,oracle=target,
                    unsafe_change=int(unsafe),match=int(dec==target),defer=int(dec=='defer'),
                    simultaneous_coverage=int(covered) if d['alternatives'] else np.nan))
    (results/'full_results.json').write_text(json.dumps(records,indent=2)+'\n')
    dump_csv(pd.DataFrame(summary),results/'comparison.csv')
    dump_csv(pd.DataFrame(metrics),results/'arm_metrics.csv')
    dump_csv(pd.DataFrame(sensitivity),results/'sensitivity.csv')
    mc=pd.DataFrame(mc); dump_csv(mc,results/'simulation_runs.csv')
    if len(mc):
        agg=mc.groupby(['scenario','method']).agg(replications=('rep','count'),unsafe_changes=('unsafe_change','sum'),
            unsafe_rate=('unsafe_change','mean'),match_rate=('match','mean'),defer_rate=('defer','mean'),coverage=('simultaneous_coverage','mean')).reset_index()
        dump_csv(agg,results/'simulation_summary.csv')
    (results/'environment.json').write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,replications=replications,seed=20261015),indent=2)+'\n')
    lines=['# Reproducible synthetic comparisons','','All outcomes are generated. Decision settings are illustrative.','','| Scenario | Day | Claims point | Gross point | Strong conventional | Integrated | Oracle diagnostic |','|---|---:|---|---|---|---|---|']
    for r in summary: lines.append('| '+' | '.join(str(r[k]) for k in ['scenario','day','claims_point','gross_point','strong_conventional','integrated','oracle_full_cohort'])+' |')
    (results/'COMPARISON.md').write_text('\n'.join(lines)+'\n')
    manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.suffix in ('.csv','.json') and p.name!='sha256.json'}
    (results/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(pd.DataFrame(summary).to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',default='.'); p.add_argument('--replications',type=int,default=60)
    args=p.parse_args(); run(args.output,args.replications)
