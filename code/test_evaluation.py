"""Behavioral, adversarial, and mathematical checks, not external validation."""
import unittest
from dataclasses import replace
from copy import deepcopy
import numpy as np
import pandas as pd
from evaluation import Config, generate, validate, snapshot, recommend, bounds

class EvaluationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a,cls.e,cls.o,cls.c=generate('narrow_sufficient')

    def test_deterministic_inputs_and_random_assignment(self):
        a,e,o,c=generate('narrow_sufficient')
        pd.testing.assert_frame_equal(a,self.a); pd.testing.assert_frame_equal(e,self.e)
        self.assertEqual(o,self.o)
        means=a.groupby('arm').requested_amount.mean()
        self.assertLess(means.max()-means.min(),2.)

    def test_no_future_information_leakage(self):
        early=snapshot(self.a,self.e,14,self.c)
        self.assertEqual(float(early.recovery.sum()),0)
        changed=self.e.copy()
        changed.loc[changed.available_day>14,'amount']=1e9
        pd.testing.assert_frame_equal(early,snapshot(self.a,changed,14,self.c))

    def test_available_time_not_event_time(self):
        idx=self.e[self.e.kind=='recognized_fraud_loss'].iloc[0]
        at_event=snapshot(self.a,self.e,int(idx.event_day),self.c)
        self.assertEqual(float(at_event.recognized_fraud_loss.sum()),0)
        at_known=snapshot(self.a,self.e,int(idx.available_day),self.c)
        self.assertGreater(float(at_known.recognized_fraud_loss.sum()),0)

    def test_changing_oracle_has_no_effect(self):
        before=recommend(snapshot(self.a,self.e,90,self.c),self.c)
        o=deepcopy(self.o); o['loss']['narrow']=1e12
        self.assertEqual(before,recommend(snapshot(self.a,self.e,90,self.c),self.c))

    def test_complete_evidence_equals_strong_baseline(self):
        x=snapshot(self.a,self.e,90,self.c)
        self.assertEqual(recommend(x,self.c),recommend(x,self.c,'strong_conventional'))

    def test_pending_uncertainty_and_unreported_tails_defer(self):
        for sc in ('uncertain_labels','unreported_tail'):
            a,e,o,c=generate(sc)
            x=snapshot(a,e,90,c)
            self.assertEqual(recommend(x,c)['decision'],'defer')
            self.assertTrue((x.loss_hi>=x.loss_lo).all())

    def test_missing_labels_do_not_force_deferral_if_bounds_support_change(self):
        a,e,o,c=generate('incomplete_legitimate_review')
        self.assertEqual(recommend(snapshot(a,e,90,c),c)['decision'],'narrow')

    def test_nonrandom_data_cannot_establish_change(self):
        a,e,o,c=generate('no_overlap')
        self.assertEqual(recommend(snapshot(a,e,90,c),c)['decision'],'defer')
        x=snapshot(self.a,self.e,90,self.c)
        self.assertEqual(recommend(x,replace(self.c,randomized=False))['decision'],'defer')

    def test_positive_value_does_not_always_mean_narrow(self):
        for sc,want in [('protective','retain'),('narrow_sufficient','narrow'),('retire_redundant','retire')]:
            a,e,o,c=generate(sc)
            self.assertEqual(recommend(snapshot(a,e,90,c),c)['decision'],want)

    def test_early_cohort_not_auto_mature(self):
        self.assertEqual(recommend(snapshot(self.a,self.e,14,self.c),self.c)['decision'],'defer')

    def test_duplicate_and_unlinked_events_rejected(self):
        with self.assertRaises(ValueError): validate(self.a,pd.concat([self.e,self.e.iloc[:1]]),self.c)
        e=self.e.copy(); e.loc[0,'account_id']=-1
        with self.assertRaises(ValueError): validate(self.a,e,self.c)
        with self.assertRaises(ValueError): validate(pd.concat([self.a,self.a.iloc[:1]]),self.e,self.c)

    def test_recovery_before_recognition_rejected(self):
        e=self.e.copy(); idx=e.index[e.kind=='recovery'][0]
        e.loc[idx,['event_day','available_day']]=[0,0]
        with self.assertRaises(ValueError): validate(self.a,e,self.c)

    def test_support_must_be_prespecified_and_respected(self):
        a=self.a.copy(); a.loc[0,'requested_amount']=201
        with self.assertRaises(ValueError): validate(a,self.e,self.c)
        with self.assertRaises(ValueError): validate(self.a,self.e,replace(self.c,unreported_cap=-.1))
        a=self.a.copy(); a.loc[0,'assignment_probability']=.01
        with self.assertRaises(ValueError): validate(a,self.e,self.c)

    def test_commercial_claim_not_fraud_loss(self):
        x=snapshot(self.a,self.e,90,self.c)
        e=self.e[self.e.kind!='commercial_claim']
        y=snapshot(self.a,e,90,self.c)
        np.testing.assert_array_equal(x.net,y.net)

    def test_approval_and_policy_release_differ(self):
        x=snapshot(self.a,self.e,90,self.c)
        self.assertTrue((x.downstream_declined>0).any())
        self.assertLess(x.approved.sum(),len(x)-x.policy_declined.sum())

    def test_bernstein_nonzero_width_for_all_zero_losses(self):
        x=snapshot(self.a,self.e,90,self.c)
        x['loss_lo']=x['loss_hi']=0.
        lo,hi=bounds(x,'narrow','loss_lo','loss_hi',self.c)
        self.assertLess(lo,0); self.assertGreater(hi,0)

    def test_unreported_cap_widens_bounds(self):
        a,e,o,c=generate('unreported_tail')
        lo=snapshot(a,e,90,replace(c,unreported_cap=0))
        hi=snapshot(a,e,90,replace(c,unreported_cap=1))
        self.assertTrue((hi.loss_hi>=lo.loss_hi).all())

    def test_tighter_confidence_widens_interval(self):
        x=snapshot(self.a,self.e,90,self.c)
        a=bounds(x,'narrow','loss_lo','loss_hi',replace(self.c,alpha=.1))
        b=bounds(x,'narrow','loss_lo','loss_hi',replace(self.c,alpha=.01))
        self.assertLessEqual(b[0],a[0]); self.assertGreaterEqual(b[1],a[1])

    def test_zero_tolerance_can_prevent_change(self):
        x=snapshot(self.a,self.e,90,self.c)
        self.assertNotEqual(recommend(x,replace(self.c,loss_margin=0))['decision'],'narrow')

if __name__=='__main__': unittest.main()
