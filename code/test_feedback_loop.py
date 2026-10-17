"""Evidence availability, source tracking, and case separation checks."""
import unittest
import pandas as pd
from build_feedback_loop import evidence_snapshot

class LoopTests(unittest.TestCase):
    def setUp(self):
        self.accounts = pd.DataFrame({'account_id':[1,2,3],'arm':['retain','narrow','retire']})
        self.events = pd.DataFrame([
            {'account_id':1,'kind':'commercial_claim','available_day':5,'amount':25},
            {'account_id':1,'kind':'legitimate_review','available_day':6,'amount':0},
            {'account_id':2,'kind':'submitted_claim','available_day':10,'amount':100},
            {'account_id':2,'kind':'fraud_review','available_day':7,'amount':0},
            {'account_id':2,'kind':'recognized_fraud_loss','available_day':23,'amount':100},
            {'account_id':2,'kind':'recovery','available_day':75,'amount':30},
            {'account_id':3,'kind':'pending_target_classification','available_day':12,'amount':70},
        ])
    def test_day14_does_not_consume_future_loss_or_recovery(self):
        data=evidence_snapshot(self.accounts,self.events,14)['totals']
        self.assertEqual(data['recognized_fraud_loss']['records'],0)
        self.assertEqual(data['recovery']['records'],0)
        self.assertEqual(data['pending_target_classification']['records'],1)
    def test_day90_recovers_recorded_amounts(self):
        data=evidence_snapshot(self.accounts,self.events,90)['totals']
        self.assertEqual(data['recognized_fraud_loss']['amount'],100)
        self.assertEqual(data['recovery']['amount'],30)
    def test_dispute_is_not_fraud_label(self):
        data=evidence_snapshot(self.accounts,self.events,90)['totals']
        self.assertEqual(data['unfiltered_claim_proxy']['accounts'],2)
        self.assertEqual(data['commercial_claim']['accounts'],1)
        self.assertEqual(data['fraud_review']['accounts'],1)
    def test_valid_arm_join(self):
        by_arm=evidence_snapshot(self.accounts,self.events,90)['by_arm']
        self.assertEqual(by_arm['retain']['commercial_claim']['count'],1)
        self.assertEqual(by_arm['narrow']['recovery']['amount'],30)
        self.assertEqual(by_arm['retire']['pending_target_classification']['count'],1)
if __name__=='__main__': unittest.main()
