"""Documented synthetic dispute-recovery policy scenario for D04 v8.

This is NOT a randomized causal effect, production outcome or a card-network
rule prediction. Source recognized loss and recovery come from existing events.
The separate formula models *possible recovery* for already confirmed claims.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class RecoveryPolicy:
    eligible_share: float
    filing_share: float
    win_share: float
    collection_share: float

BASELINE = RecoveryPolicy(0.75, 0.80, 0.625, 0.80)
PROPOSED = RecoveryPolicy(0.85, 0.90, 0.70, 0.90)

def predicted_recovery(confirmed_gross_loss, policy):
    if confirmed_gross_loss < 0 or any(not 0<=v<=1 for v in policy.__dict__.values()):
        raise ValueError('Invalid exposure or recovery policy probability')
    return confirmed_gross_loss * policy.eligible_share * policy.filing_share * policy.win_share * policy.collection_share

def projected_change(confirmed_gross_loss, observed_recovery, policy, baseline=BASELINE):
    """Scenario only; assumes confirmed gross, other factors fixed and same cohort.

    Does not change observed event ledger and must not be added to a randomized
    rule-effect estimate without re-estimating joint arms.
    """
    if observed_recovery < 0 or observed_recovery > confirmed_gross_loss:
        raise ValueError('Invalid observed recovered dollars')
    baseline_model=predicted_recovery(confirmed_gross_loss,baseline)
    projected=predicted_recovery(confirmed_gross_loss,policy)
    return {'observed_recovered':observed_recovery,
            'baseline_model_recovery':baseline_model,
            'policy_scenario_recovery':projected,
            'illustrative_incremental_recovery':projected-baseline_model,
            'illustrative_net_loss':max(0,confirmed_gross_loss-observed_recovery-(projected-baseline_model))}
