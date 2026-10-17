"""Reproducibility and accounting checks for the ~2% synthetic dollar-impact bridge."""
import unittest
import pandas as pd
from build_feedback_loop import build
from build_dashboard import load_data

class DollarImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=build()

    def test_retained_rule_roughly_two_percent_real_data(self):
        for scenario in self.data.values():
            r=scenario['checkpoints']['90']['arms']['retain']
            self.assertAlmostEqual(r['decline_rate'],r['policy_declines']/r['n'])
            self.assertTrue(.019<=r['decline_rate']<=.021)

    def test_precision_recall_and_good_bad_dollars_reconcile(self):
        for scenario in self.data.values():
            r=scenario['checkpoints']['90']['arms']['retain']
            b=r['policy_blocked_requested_dollars'];good=r['good_policy_blocked_requested_dollars'];bad=r['bad_policy_blocked_requested_dollars'];allbad=r['all_fraud_requested_dollars']
            self.assertAlmostEqual(good+bad,b)
            self.assertAlmostEqual(bad/b,r['dollar_precision'])
            self.assertAlmostEqual(bad/allbad,r['dollar_recall'])
            self.assertEqual(r['policy_declines'],r['bad_policy_declines']+r['good_policy_declines'])

    def test_one_percent_interchange_upper_proxy(self):
        for scenario in self.data.values():
            x=scenario['checkpoints']['90'];r=x['arms']['retain']
            self.assertAlmostEqual(x['dollar_impact']['blocked_interchange_upper_bound'],round(.01*r['good_policy_blocked_requested_dollars'],2))

    def test_alternative_net_benefit_only_when_mature(self):
        mature=self.data['narrow_sufficient']['checkpoints']['90']
        for alternative in ('narrow','retire'):
            d=mature['dollar_impact']['tested_alternatives'][alternative]
            self.assertTrue(d['can_treat_as_mature'])
            self.assertAlmostEqual(d['illustrative_net_financial_delta'],round(d['illustrative_interchange_change']-d['incremental_recognized_net_fraud_loss'],2))
        self.assertFalse(self.data['narrow_sufficient']['checkpoints']['14']['dollar_impact']['tested_alternatives']['narrow']['can_treat_as_mature'])
        self.assertFalse(self.data['uncertain_labels']['checkpoints']['90']['dollar_impact']['tested_alternatives']['narrow']['can_treat_as_mature'])

    def test_feedback_cycle_uses_new_events_and_changes_state(self):
        a=self.data['narrow_sufficient'];b=self.data['uncertain_labels'];
        self.assertEqual(a['feedback_cycle']['first_decision'],'defer')
        self.assertEqual(a['feedback_cycle']['updated_decision'],'narrow')
        self.assertEqual(b['feedback_cycle']['updated_decision'],'defer')
        self.assertGreater(b['feedback_cycle']['still_pending_target_labels'],0)
        self.assertEqual(a['checkpoints']['90']['arms']['retain']['dollar_precision'],b['checkpoints']['90']['arms']['retain']['dollar_precision'])
        self.assertEqual(a['feedback_cycle']['new_recognized_dollars'],a['checkpoints']['90']['feedback']['totals']['recognized_fraud_loss']['amount']-a['checkpoints']['14']['feedback']['totals']['recognized_fraud_loss']['amount'])

if __name__=='__main__':unittest.main()
