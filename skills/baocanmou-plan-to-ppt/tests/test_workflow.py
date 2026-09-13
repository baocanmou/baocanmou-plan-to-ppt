import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
intake, plancheck, impact = [module(n) for n in ('intake','plancheck','impact')]

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'examples/plan.json').read_text(encoding='utf-8'))
        self.sources=json.loads((ROOT/'examples/sources.json').read_text(encoding='utf-8'))
    def check(self): return plancheck.check(self.plan,self.sources)
    def test_complete_demo(self): self.assertTrue(self.check()['passed'])
    def test_quote_must_exist(self):
        self.plan['claims'][0]['sources'][0]['quote']='捏造的确认原话'
        self.assertFalse(self.check()['passed'])
    def test_unknown_needs_visible_disclosure(self):
        claim = next(c for c in self.plan['claims'] if c['id']=='F-budget')
        claim['kind']='unknown'
        slide = next(s for s in self.plan['slides'] if claim['id'] in s['claim_ids'])
        slide.pop('disclosure', None)
        self.assertTrue(any('unresolved fact needs a visible disclosure' in e for e in self.check()['errors']))
    def test_chart_typo(self):
        self.plan['slides'][2]['chart']['series'][0]['values'][0]=540
        self.assertFalse(self.check()['passed'])
    def test_typo_and_binding_edit_still_need_source(self):
        c=self.plan['slides'][2]['chart'];c['series'][0]['values'][0]=540
        c['bindings'][0]['value']=540;c.pop('totals')
        self.assertTrue(any('absent' in e for e in self.check()['errors']))
    def test_category_swap_wide_quote(self):
        c=self.plan['slides'][2]['chart']
        quote=next(x for x in self.plan['claims'] if x['id']=='F-interview')['sources'][0]['quote']
        for b in c['bindings']: b['quote']=quote
        self.assertTrue(self.check()['passed'])
        c['categories'][0],c['categories'][1]=c['categories'][1],c['categories'][0]
        self.assertTrue(any('label differs' in e for e in self.check()['errors']))
    def test_numeric_table_cell_cannot_lose_binding(self):
        self.plan['slides'][8]['table']['bindings'].pop()
        self.assertFalse(self.check()['passed'])
    def test_table_row_swap(self):
        t=self.plan['slides'][8]['table'];t['rows'][1][0],t['rows'][2][0]=t['rows'][2][0],t['rows'][1][0]
        self.assertTrue(any('label differs' in e for e in self.check()['errors']))
    def test_bad_table_sum(self):
        self.plan['slides'][8]['table']['totals'][0]['expected']=70000
        self.assertTrue(any('total mismatch' in e for e in self.check()['errors']))
    def test_new_material_requires_review(self):
        new=copy.deepcopy(self.sources);new['chunks'].append({'id':'new:line:1','sha256':'abc','text':'新增信息'})
        r=impact.impact(self.plan,self.sources,new)
        self.assertTrue(r['review_required']);self.assertEqual(r['affected_slides'],[])
    def test_changed_budget_locates_direct_pages(self):
        new=copy.deepcopy(self.sources)
        next(c for c in new['chunks'] if '最终确认：预算上限' in c['text'])['sha256']='changed'
        r=impact.impact(self.plan,self.sources,new)
        self.assertEqual({s['id'] for s in r['affected_slides']},{'S02','S09','S10','S12'})

class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_unicode_and_line_locator(self):
        p=self.d/'资料.md';p.write_text('预算6万元\n\n负责人确认',encoding='utf-8')
        r=intake.build([p]);self.assertEqual([x['locator'] for x in r['chunks']],['line:1','line:3'])
        self.assertNotIn(str(self.d),json.dumps(r,ensure_ascii=False))
    def test_invalid_encoding_is_visible_failure(self):
        p=self.d/'bad.txt';p.write_bytes(b'\xff\xfe')
        self.assertEqual(len(intake.build([p])['failures']),1)
    def test_duplicate_names_fail_instead_of_merge(self):
        p=self.d/'data.md';p.write_text('资料',encoding='utf-8')
        self.assertEqual(len(intake.build([p,p])['failures']),1)
    def test_docx_body_table_order(self):
        p=self.d/'资料.docx'
        xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>先读</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>预算</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:t>后读</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(p,'w') as z:z.writestr('word/document.xml',xml)
        self.assertEqual([x['text'] for x in intake.extract(p)],['先读','预算','后读'])
    def test_pptx_relationship_order(self):
        p=self.d/'资料.pptx';ns='http://schemas.openxmlformats.org/'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{ns}presentationml/2006/main" xmlns:r="{ns}officeDocument/2006/relationships"><p:sldIdLst><p:sldId r:id="r2"/><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/><Relationship Id="r2" Target="slides/slide2.xml"/></Relationships>')
            for i in (1,2):z.writestr(f'ppt/slides/slide{i}.xml',f'<a:t xmlns:a="{ns}drawingml/2006/main">第{i}张</a:t>')
        self.assertEqual([x['text'] for x in intake.extract(p)],['第2张','第1张'])

if __name__=='__main__': unittest.main()
