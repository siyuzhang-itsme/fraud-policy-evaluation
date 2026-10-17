"""Business-metric unit tests for the synthetic rule-governance dashboard."""
import unittest
import pandas as pd
from build_dashboard import metric_snapshot


class DashboardTests(unittest.TestCase):
    def frame(self, missing=False):
        rows=[]
        # Four accounts per synthetic policy arm: two independently reviewed
        # fraud-intent cases and two reviewed legitimate ones.
        for arm in ('retain','narrow','retire'):
            for idx in range(4):
                declined = (arm=='retain' and idx in (0,2)) or (arm=='narrow' and idx==0)
                reviewed = not (missing and arm=='retain' and idx==2)
                rows.append(dict(arm=arm,requested_amount=100,policy_declined=int(declined),
                   fraud_review=int(idx<2 and reviewed),legitimate_review=int(idx>=2 and reviewed),
                   approved=int(not declined),net=0,financial_horizon_closed=1,
                   pending_target_classification=0))
        return pd.DataFrame(rows)

    def test_precision_recall_independent_audit_denominators(self):
        t=metric_snapshot(self.frame())
        self.assertAlmostEqual(t['retain']['decline_rate'], 0.5)
        self.assertAlmostEqual(t['retain']['unit_precision'], 0.5)
        self.assertAlmostEqual(t['retain']['unit_recall'], 0.5)
        self.assertAlmostEqual(t['retain']['dollar_precision'], 0.5)
        self.assertAlmostEqual(t['narrow']['dollar_precision'], 1.0)
        self.assertIsNone(t['retire']['dollar_precision'])
        self.assertEqual(t['retire']['dollar_recall'], 0.0)

    def test_incomplete_audit_blocks_unqualified_precision(self):
        t=metric_snapshot(self.frame(missing=True))
        self.assertLess(t['retain']['audit_coverage'],1)
        self.assertIsNone(t['retain']['unit_precision'])
        self.assertIsNone(t['retain']['dollar_recall'])
        self.assertAlmostEqual(t['narrow']['audit_coverage'],1.0)

if __name__=='__main__':unittest.main()
