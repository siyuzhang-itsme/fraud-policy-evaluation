"""Reproduce four comparison methods on fictional D04 policy snapshots.

Claims-point and gross-point deliberately omit consumer access/cost and prioritize
retirement. They are weak illustration baselines, not typical practice benchmarks.
Strong conventional respects access/cost but prematurely treats observed loss
as fully reconciled. This contrast must not be generalized to actual industry results.
"""
import json
from pathlib import Path
import pandas as pd
from evaluation import Config,snapshot,recommend

ROOT=Path(__file__).resolve().parents[1]
METHODS={
    "claims_point":"Submitted-claims point estimate, no maturity/access/cost guardrail.",
    "gross_point":"Gross-loss point estimate, no maturity/access/cost guardrail.",
    "strong_conventional":"Access/cost-aware bounded comparison assuming present outcomes complete.",
    "integrated":"Maturity-aware, label-uncertainty-aware comparison with access/cost safeguards.",
}
EXPECTED={
 ("narrow_sufficient",14):("retire","retire","retire","defer"),
 ("narrow_sufficient",90):("retire","retire","narrow","narrow"),
 ("uncertain_labels",14):("retire","retire","retire","defer"),
 ("uncertain_labels",90):("retire","retire","retire","defer"),
}

def build(write=True):
    results={"schema":"d04-v11-method-comparison-1","synthetic_only":True,
             "method_order":list(METHODS),"method_descriptions":METHODS,"scenarios":[],
             "limitations":["The two point baselines ignore access/cost and prioritize retire.",
                "Strong conventional is a stronger comparator but assumes presently observed loss is complete.",
                "These fictional settings do not demonstrate superior results in every real setting."]}
    for scenario,label in (("narrow_sufficient","Narrower rule sufficient"),
                           ("uncertain_labels","Labels remain uncertain")):
        files=[ROOT/"data"/f"{scenario}_{s}.csv" for s in ("accounts","events")]
        files.append(ROOT/"data"/f"{scenario}_config.json")
        missing=[str(p.relative_to(ROOT)) for p in files if not p.exists()]
        if missing:
            raise FileNotFoundError("Run python code/generate_demo_inputs.py first; missing: "+", ".join(missing))
        a=pd.read_csv(files[0]);e=pd.read_csv(files[1])
        cfg=Config(**json.loads(files[2].read_text(encoding="utf-8")))
        checkpoints=[]
        for day in (14,90):
            observed=snapshot(a,e,day,cfg)
            decisions={name:recommend(observed,cfg,name)["decision"] for name in METHODS}
            assert tuple(decisions.values())==EXPECTED[(scenario,day)],(scenario,day,decisions)
            checkpoints.append({"day":day,"decisions":decisions})
        results["scenarios"].append({"id":scenario,"label":label,"checkpoints":checkpoints})
    if write:
        p=ROOT/"results"/"baseline_comparison.json"
        p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("Wrote reproducible four-method comparison:",p)
    return results

if __name__=="__main__":
    build()
