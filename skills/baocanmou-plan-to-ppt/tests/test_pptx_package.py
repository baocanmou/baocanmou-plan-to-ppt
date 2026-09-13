import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pptxcheck',ROOT/'scripts/pptxcheck.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class DeliveredPackageTests(unittest.TestCase):
    def setUp(self):
        self.sample=ROOT/'examples/山间来信_策划提案示范.pptx'
        self.plan=json.loads((ROOT/'examples/plan.json').read_text(encoding='utf-8'))
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def mutate(self, editor):
        out=Path(self.tmp.name)/'altered.pptx'
        with zipfile.ZipFile(self.sample) as z,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as target:
            for item in z.infolist():target.writestr(item,editor(item.filename,z.read(item.filename)))
        return checker.check(out,self.plan)
    def test_native_objects_and_embedded_chart_data(self):
        r=checker.check(self.sample,self.plan)
        self.assertTrue(r['passed'],r['errors']);self.assertEqual(len(r['slides']),12)
        self.assertEqual(sum(s['native_tables'] for s in r['slides']),3)
        self.assertEqual(r['slides'][2]['native_charts'],1)
        self.assertEqual(r['slides'][2]['chart_workbooks'],1)
        self.assertTrue(all(s['native_text_objects']>0 for s in r['slides']))
    def test_final_table_number_tamper(self):
        changed=[]
        def edit(name,data):
            if name.startswith('ppt/slides/') and name.endswith('.xml'):
                root=ET.fromstring(data)
                for t in root.findall('.//a:tbl//a:t',checker.NS):
                    if t.text=='15000':t.text='15001';changed.append(name)
                data=ET.tostring(root,encoding='utf-8')
            return data
        r=self.mutate(edit);self.assertEqual(len(changed),1)
        self.assertTrue(any('native table rows/values differ' in e for e in r['errors']))
    def test_final_chart_cache_tamper(self):
        changed=[]
        def edit(name,data):
            if name.endswith('.xml') and '/charts/' in name:
                root=ET.fromstring(data)
                for t in root.findall('.//c:numCache/c:pt/c:v',checker.NS):
                    if t.text=='54':t.text='540';changed.append(name)
                data=ET.tostring(root,encoding='utf-8')
            return data
        r=self.mutate(edit);self.assertEqual(len(changed),1)
        self.assertTrue(any('native chart categories/values differ' in e for e in r['errors']))
    def test_final_visible_disclosure_cannot_disappear(self):
        disclosure=self.plan['slides'][2]['disclosure'];changed=[]
        def edit(name,data):
            if name.endswith('.xml') and name.startswith('ppt/slides/'):
                root=ET.fromstring(data)
                for t in root.findall('.//a:t',checker.NS):
                    if disclosure in (t.text or ''):t.text=t.text.replace(disclosure,'');changed.append(name)
                data=ET.tostring(root,encoding='utf-8')
            return data
        r=self.mutate(edit);self.assertEqual(len(changed),1)
        self.assertTrue(any('visible disclosure missing' in e for e in r['errors']))

if __name__=='__main__':unittest.main()
