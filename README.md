# Fraud Policy Evaluation — Payment Decisions, Disputes & Recovery

[![Zenodo DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23442713.svg)](https://doi.org/10.5281/zenodo.23442713)

**Stop Fraud. Protect Legitimate Payments. Recover Losses.**

A reproducible **fictional** demonstration of two connected consumer-financial risk decisions: (1) payment screening and rule governance, and (2) dispute handling and recovery policy. The example shows how later evidence can improve decisions without using real account, customer, employer, or production-rule data.

**[Open the interactive English dashboard](docs/index.html)** — download the HTML file and open it locally in a browser. The page requires no backend or account.

## What the demo illustrates

- A fictional payment rule declines about **2%** of eligible requests with approximately **10% dollar precision** and **29% dollar recall** in its tested arm.
- The arithmetic separates **$6,100 in fictional fraud-intent requested dollars blocked** from **$543.50 in potential interchange opportunity cost** under an illustrative 1% rate. A **separate** mature policy-arm comparison illustrates **+$4,172.74** in protective value; these amounts must not be directly subtracted from one another.
- Follow-up fraud disputes, classification checks, recoveries and review horizons can change the appropriate **retain / refine / retire / defer** recommendation.
- A distinct dispute-policy teaching example considers **accept / investigate / deny**, and an **illustrative recovery-policy scenario** examines how chargeback eligibility, filing, win rate and collection affect net loss.

Click the flow diagram's six STEP links to inspect evidence and calculations. The disputed-claim vignettes are teaching examples rather than logged claim-adjudication observations.

## Reproduce it

Requires Python 3.11+, NumPy and pandas:

```bash
python -m pip install -r requirements.txt
python code/generate_demo_inputs.py
python -m unittest discover -s code -p 'test_*.py' -q
python code/build_feedback_loop.py
python code/build_baseline_comparison.py
python code/build_v11.py
```

The first command generates **fictional CSV accounts and events** from a fixed seed; the input files are not real customer records. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and the current v11 [evaluation outputs](results/feedback_loop_metrics.json). The dashboard is already bundled at `docs/index.html`.

## Limits

- Blocked fraud-intent requested dollars are not necessarily actual avoided fraud losses.
- Submitted disputes are not automatically confirmed fraud; a claim decision requires evidence and applicable consumer-protection procedures.
- The synthetic recovery-policy sliders are **assumptions**, not observed recovery improvements, actual chargeback rights or causal production estimates.
- This prototype does not establish real-world deployment, peer review, or third-party adoption.

**Concept and professional framing:** Siyu Zhang. **Implementation:** AI-assisted demonstration code, subject to substantive expert review and iterative validation. Do not infer independent software authorship or an audited real-world financial effect solely from this publication.

**License:** [MIT License](LICENSE). Reuse of the software and associated documentation is permitted under its terms; all example data and metrics are fictional.

**Cite this software:** Zhang, Siyu (2026). *Fraud Policy Evaluation: Payment Decisions, Disputes and Recovery* (v1.0.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.23442713. See [CITATION.cff](CITATION.cff) for machine-readable metadata. This DOI identifies the archived **v1.0.0 release**, not later changes to the main branch.
