import unittest
from dispute_overlay import RecoveryPolicy, BASELINE, PROPOSED, predicted_recovery, projected_change

class TestDisputeRecoveryOverlay(unittest.TestCase):
    def test_baseline_recovery_share(self):
        self.assertAlmostEqual(predicted_recovery(13700,BASELINE),4110)
    def test_upgrade_is_positive(self):
        a=projected_change(13700,4110,PROPOSED)
        self.assertGreater(a['illustrative_incremental_recovery'],0)
        self.assertLess(a['illustrative_net_loss'],9590)
    def test_zero_confirmed_exposure(self):
        self.assertEqual(predicted_recovery(0,PROPOSED),0)
    def test_invalid_policy_rejected(self):
        with self.assertRaises(ValueError):
            predicted_recovery(100,RecoveryPolicy(1.2,.8,.5,.8))
    def test_invalid_observed_recovery(self):
        with self.assertRaises(ValueError):
            projected_change(100,150,PROPOSED)
    def test_baseline_has_no_increment(self):
        self.assertAlmostEqual(projected_change(3500,1050,BASELINE)['illustrative_incremental_recovery'],0)

if __name__=='__main__':unittest.main()
