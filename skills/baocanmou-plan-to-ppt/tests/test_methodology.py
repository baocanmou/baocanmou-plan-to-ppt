import json
import unittest
from test_workflow import ROOT,plancheck

class MethodologyBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'examples/plan.json').read_text(encoding='utf-8'))
        self.sources=json.loads((ROOT/'examples/sources.json').read_text(encoding='utf-8'))
    def result(self):return plancheck.check(self.plan,self.sources)
    def test_design_without_positioning_is_rejected(self):
        self.plan['methodology']['shu'][0]['mao_id']='missing-position'
        self.assertTrue(any('design needs a valid positioning' in e for e in self.result()['errors']))
    def test_communication_without_design_is_rejected(self):
        self.plan['methodology']['ming'][0]['shu_ids']=[]
        self.assertTrue(any('existing design/expression' in e for e in self.result()['errors']))
    def test_missing_inputs_cannot_be_called_full_application(self):
        self.plan['methodology']['mode']='full'
        errors=self.result()['errors']
        self.assertTrue(all(any(field in e for e in errors) for field in ('assessment_claim_ids','source_card_claim_ids','founder_claim_ids')))
    def test_unknown_vision_must_remain_visible(self):
        next(s for s in self.plan['slides'] if s['id']=='S02').pop('disclosure')
        self.assertTrue(any('unresolved fact needs a visible disclosure' in e for e in self.result()['errors']))
    def test_nonbrand_plan_can_omit_brand_method(self):
        self.plan.pop('methodology')
        self.assertTrue(self.result()['passed'])

if __name__=='__main__':unittest.main()
