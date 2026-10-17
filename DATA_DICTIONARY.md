# Input and output specification

All amounts are fictional U.S. dollars. Days are elapsed days after one index authorization attempt. Every account contributes one attempt. The model omits retries, linked accounts, repeated transactions and temporal dependence.

## Observed account file

| Field | Meaning |
|---|---|
| account_id | Unique generated integer account and assignment unit |
| arm | retain, narrow, or retire the tested restriction; mandatory downstream checks remain |
| segment | Prespecified fictional decision segment 0 high risk, 1 marginal, 2 outside coverage; assigned before treatment |
| requested_amount | Requested amount before tested treatment; support is fixed in config, not inferred from sample |
| policy_declined | Tested restriction blocked the attempt |
| downstream_declined | Attempt passed tested restriction but another check declined it |
| approved | Final authorization approved; exactly one of the three handling fields is 1 |
| assignment_probability | Logged probability, 1/3 for randomized examples; metadata is a declaration, not proof that randomization occurred |

The evaluator uses raw randomized-arm means, not inverse-propensity weighting. The example supports equal probability independent assignment only. Unequal or covariate-dependent allocation, persistent clusters, crossovers, outages and failed assignment require additional implementation. They must not be analyzed by merely editing this probability field.

## Observed event file

| Field | Meaning |
|---|---|
| event_id | Globally unique within a scenario |
| account_id | Link to original index attempt |
| kind | Event category below |
| event_day | When the underlying event occurred |
| available_day | When the evaluator could know it; snapshots filter on this field |
| amount | Nonnegative linked event amount; zero for evidence and horizon-closure events |

| Event kind | Evaluation meaning |
|---|---|
| legitimate_review | Supported legitimate intent from a stipulated independent audit, not absence of a claim |
| fraud_review | Supported unauthorized intent from that audit; intent evidence does not itself settle institutional liability |
| commercial_claim | Non-target commercial dispute; excluded from recognized target fraud loss |
| submitted_claim | Reported claim, not automatically recognized fraud loss |
| pending_target_classification | Submitted amount whose recognized target-loss treatment is unresolved; upper-bound exposure, not booked loss |
| recognized_fraud_loss | Institution-borne target fraud loss recognized under the fictional accounting definition |
| recovery | Offset linked to recognized loss from the same account, horizon and perspective |
| financial_horizon_closed | All target-loss and recovery information through the declared day-90 horizon is complete; not a legitimacy label or lifetime closure |

Closure at day 90 is a generator convention, not an industry maturity rule. Blocked attempts close immediately for index-attempt financial loss because this example assumes no settlement following a decline. Real reversals and settlement exceptions need additional events. Loss corrections, partial recoveries in multiple currencies, reopened cases, claim reassignment and overlapping classification updates are not implemented. Inputs violating current rules are rejected rather than repaired automatically.

## Config file

`n` is total accounts across all arms. `loss_margin` is maximum tolerable additional target net loss per enrolled account. `intervention_cost` and `denial_cost` are separate hypothetical weights for a legitimate policy intervention and a legitimate final denial; both can apply, so set them to represent distinct burdens rather than double-counting the same harm. `min_cost_gain` is the minimum reduction in this burden measure. `access_margin` is maximum tolerable reduction in legitimate approved attempts per enrolled account. These are normative settings, not employer settings or validated consumer valuations.

`max_amount` declares a genuine upper bound on index-attempt loss. Exceeding it is rejected. It must be changed before analysis when the eligible population has a different support. Sample maxima must not be substituted. `alpha` applies to one prespecified snapshot and family of comparisons. `inference=bernstein` is the conservative default; `normal` is an approximate sensitivity alternative. `unreported_cap=1` permits all remaining unclosed approved exposure to become target loss. Smaller values are substantive assumptions; 0 silently excludes unreported loss and is shown only as an adverse sensitivity. `randomized` is a design declaration whose correctness must be separately audited.

## Derived measures

Every rate in the primary decision uses all assigned accounts, including declines. `net_bps` is descriptive net loss divided by requested authorization dollars, multiplied by 10,000. It has no separate bps confidence interval; the decision uses dollars per enrolled account. `supported_legitimate_approved_per_account` is a joint event per all assigned accounts, not approval conditional on selectively observed legitimacy. `unknown_intent_fraction` includes unresolved and unreviewed intent. `open_financial_fraction` concerns financial follow-up, a distinct concept.

`loss_lo` and `loss_hi` bound final horizon net loss. `access_lo/hi` bound the legitimate-and-approved indicator. `cost_lo/hi` bound illustrative legitimate consumer burden. Endpoint uncertainty intervals include sampling uncertainty; raw endpoint gaps themselves are identification ranges, not confidence intervals.

`comparison.csv` contains all four recommendations for each scenario and cutoff. `arm_metrics.csv` contains observed arm measures. `full_results.json` contains alternative-specific endpoint intervals and supported, rejected or unresolved statuses. `sensitivity.csv` varies one setting at a time; it is not a joint robustness envelope. `simulation_runs.csv` preserves each independent seeded experiment. `simulation_summary.csv` reports match, deferral, unsafe-change and simultaneous-coverage diagnostics. Oracle equality is exact superpopulation arithmetic, not recovered counterfactual truth. `sha256.json` records input and result hashes for the run.

## Dollar-impact fields (dashboard v2)

The newer two-scenario preview sets the synthetic broad-rule decline rate near 2% from regenerated accounts, not from a hard-coded display label. Original `code/evaluation.py` randomization and observation-time rules remain in force.

- `arms[retain].policy_blocked_requested_dollars`: sum of requested amounts for **rule-layer declines**, not final declined transaction value or settled volume.
- `arms[retain].bad_policy_blocked_requested_dollars`: audited fraud-intent requested dollars among those tested-rule declines; equals dollar precision times declined requested dollars.
- `arms[retain].good_policy_blocked_requested_dollars`: audited legitimate requested dollars among tested-rule declines; equals declined requested dollars minus bad declined requested dollars.
- `arms[retain].all_fraud_requested_dollars`: independently audited fraud-intent requested dollars in that same randomized arm. Bad rule-declined dollars divided by this field equals dollar recall.
- `dollar_impact.blocked_interchange_upper_bound`: hypothetical gross interchange **at risk** = rule-layer blocked legitimate requested dollars × 0.01. Do not treat as a measured merchant, issuer or network fee. It does not account for other declines, settlement or realized fees.
- `dollar_impact.tested_alternatives[*].incremental_recognized_net_fraud_loss`: (candidate arm recognized net fraud loss per eligible − retain arm recognized net loss per eligible) × retain reference arm eligible count. This includes linked recoveries available at the checkpoint, and is **provisional** if relevant horizons remain open.
- `dollar_impact.tested_alternatives[*].incremental_legitimate_final_approved_requested_dollars`: (candidate arm audited legitimate final-approved requested amount per eligible − retain arm corresponding amount) × retain reference eligible count. This uses the available fictional independent audit; **final approval is not necessarily settlement**.
- `dollar_impact.tested_alternatives[*].illustrative_interchange_change`: preceding amount × the fixed illustrative 1% opportunity rate.
- `dollar_impact.tested_alternatives[*].illustrative_net_financial_delta`: interchange change − observed extra recognized net fraud loss. Positive favors candidate vs retaining, **within this simplified proxy only**. The dashboard withholds settled labeling when follow-up is incomplete.
- `feedback_cycle`: explicit day14-to-day90 incremental recognized-loss events/dollars, linked recoveries, pending classification count, and before/after **governance decision**. Results are computed from fictional event ledgers; no new release or production intervention is executed.

The scenario's consumer-burden guardrails are *additional* to the interchange proxy, not inferred from its value. Rule change recommendations must not be read as maximizing an assumed 1% interchange margin.

## V3 synthetic decision parameters and return path

The two preview scenarios use invented `segment_mix=(0.008, 0.012, 0.98)`, `p=(0.23, 0.055, 0.0045)`, and `recovery=(0.30, 0.30, 0.30)`. Their invented guardrails are `loss_margin=0.55` dollars per eligible attempt and `min_cost_gain=0.004` in a separately declared consumer-burden index. Those values are not real employer risk budgets, interchange agreements, or fraud-prevalence measurements.

The return connection is **Governance (5) → revalidated labels (2) and updated dispute/recovery evidence (3) → benefit recalculation (4) → revised governance (5) → new monitoring window (1)**. In the supplied scenarios, the independent intent review arrives by day 7, hence the initial KPI values remain fixed; the later change comes from financial event maturity, not from modifying precision/recall through a mislabeled claim.

All dashboard percentage-to-dollar arithmetic displays rounded factors and therefore uses approximate equality. Source CSVs and generated JSON provide the exact audit quantities. `interchange_change` in the synthetic comparison is an assumed 1% of incremental finally approved **requested** legitimate dollars, not a prediction of a real merchant/issuer settlement or interchange margin.


## V8 dispute / recovery scenario (not observed policy outcomes)

The HTML shows the original ledger's `submitted_claim`, `commercial_claim`, `pending_target_classification`, `recognized_fraud_loss` and `recovery` event counts by arm. It does not infer claim acceptance, denial, or actual merchant-network filing/wins from that ledger. Separate UI options describe the decision branches. Only *confirmed* gross fraud-loss amount is used to illustrate a possible policy-specific chargeback/recovery process: `recognized_gross × eligible_fraction × filing_fraction × favorable_outcome_fraction × collection_fraction`. Baseline fractions (0.75, 0.80, 0.625, 0.80) multiply to 0.30, the synthetic generator's existing realized recovery fraction; they are explanatory parameters, not audited processor stats. Hypothetical changes are deducted from observed net loss only for illustrative scenario arithmetic—not a causal estimate. Do not add a projected recovery change to an upstream randomized-rule contrast as if independently additive.

## V9 expanded UI fields

The v9 page computes formula rows directly from the embedded `feedback_loop_metrics.json` synthetic snapshots. Day-14 comparisons and unresolved evidence do not display mature comparative values. The audit totals across all three arms appear only in the day-14/day-90 comparison; the label-quality KPI cards use the RETAIN arm. The 1% interchange on rule-declined legitimate requested dollars is distinct from incremental interchange in the finally-approved-dollar policy contrast.

## v10 visual emphasis only

The right formula branch foregrounds interchange opportunity cost (legitimate declined requested dollars × illustrative 1% interchange). Legitimate declined requested dollars remains a substep, not the final business metric. The left branch foregrounds fraud-intent declined requested dollars. v10 does not change any synthetic inputs, computation, comparison, or evidence-maturity behavior.
