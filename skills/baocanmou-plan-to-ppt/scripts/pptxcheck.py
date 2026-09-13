#!/usr/bin/env python3
"""Inspect the actual PPTX package, editability and declared content. No Office dependency."""
import argparse
import json
import math
import posixpath
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
RID = '{' + NS['r'] + '}id'


def norm(value):
    return ''.join(str(value).split())


def xml(z, name):
    info = z.getinfo(name)
    if info.file_size > 80 * 1024 * 1024:
        raise ValueError(f'Oversize XML part: {name}')
    data = z.read(name)
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity declarations are unsupported')
    return ET.fromstring(data)


def relationships(z, part):
    name = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if name not in z.namelist():
        return {}
    result = {}
    for rel in xml(z, name):
        target = rel.attrib['Target']
        if rel.attrib.get('TargetMode') == 'External':
            result[rel.attrib['Id']] = {'external': True, 'target': target}; continue
        absolute = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part), target))
        if absolute.startswith('../') or absolute not in z.namelist():
            raise ValueError(f'Missing/unsafe relationship target: {part} -> {target}')
        result[rel.attrib['Id']] = {'external': False, 'target': absolute}
    return result


def cached(node, field):
    parent = node.find(f'c:{field}', NS)
    if parent is None:
        return []
    pts = parent.findall('.//c:pt', NS)
    return [p.findtext('c:v', '', NS) for p in sorted(pts, key=lambda p: int(p.get('idx', '0')))]


def check(path, plan=None):
    errors, warnings, summary = [], [], []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            errors.append('Duplicate ZIP entries')
        if z.testzip():
            errors.append('ZIP CRC failure')
        for required in ('[Content_Types].xml', '_rels/.rels', 'ppt/presentation.xml'):
            if required not in names:
                errors.append(f'Missing {required}')
        if errors:
            return {'passed': False, 'errors': errors, 'warnings': warnings, 'slides': []}
        pres = xml(z, 'ppt/presentation.xml')
        rels = relationships(z, 'ppt/presentation.xml')
        size = pres.find('p:sldSz', NS)
        width, height = int(size.get('cx')), int(size.get('cy'))
        order = pres.findall('p:sldIdLst/p:sldId', NS)
        slides = plan.get('slides', []) if plan else []
        if plan and len(order) != len(slides):
            errors.append(f'Actual slide count {len(order)} differs from plan {len(slides)}')
        for i, item in enumerate(order, 1):
            part = rels[item.attrib[RID]]['target']; root = xml(z, part)
            slide_rels = relationships(z, part)
            texts = [t.text or '' for t in root.findall('.//a:t', NS)]
            native_text = sum(bool(''.join(t.text or '' for t in sp.findall('.//a:t', NS)).strip())
                              for sp in root.findall('.//p:sp', NS))
            if root.findall('.//p:grpSp', NS):
                warnings.append(f'slide {i}: grouped geometry requires render review')
            for obj in root.findall('p:cSld/p:spTree/*', NS):
                xfrm = obj.find('p:spPr/a:xfrm', NS)
                if xfrm is None:
                    xfrm = obj.find('p:xfrm', NS)
                if xfrm is not None and not xfrm.get('rot'):
                    off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
                    if off is not None and ext is not None:
                        x, y, w, h = [int(v) for v in (off.get('x'), off.get('y'), ext.get('cx'), ext.get('cy'))]
                        tolerance = 12700  # one point; avoids rounding false positives
                        if x < -tolerance or y < -tolerance or x + w > width + tolerance or y + h > height + tolerance:
                            errors.append(f'slide {i}: object extends outside canvas')
            tables = []
            for table in root.findall('.//a:tbl', NS):
                rows = [[ ''.join(t.text or '' for t in cell.findall('.//a:t', NS))
                          for cell in row.findall('a:tc', NS)] for row in table.findall('a:tr', NS)]
                tables.append(rows)
            charts = []
            for ref in root.findall('.//c:chart', NS):
                target = slide_rels[ref.attrib[RID]]['target']; chart_root = xml(z, target)
                chart_rels = relationships(z, target)
                ext = chart_root.find('.//c:externalData', NS)
                workbook = bool(ext is not None and ext.get(RID) in chart_rels and
                                not chart_rels[ext.get(RID)]['external'] and
                                chart_rels[ext.get(RID)]['target'].endswith('.xlsx'))
                data = []
                for series in chart_root.findall('.//c:ser', NS):
                    vals = cached(series, 'val')
                    data.append({'categories': cached(series, 'cat'), 'values': [float(v) for v in vals]})
                charts.append({'series': data, 'embedded_workbook': workbook})
                if not workbook:
                    warnings.append(f'slide {i}: chart has no embedded XLSX; cross-app editability unverified')
            if plan and i <= len(slides):
                expected = slides[i-1]
                joined = norm(''.join(texts))
                if norm(expected['title']) not in joined:
                    errors.append(f'slide {i}: planned title missing from native text')
                for required in expected.get('required_text', []):
                    if norm(required) not in joined:
                        errors.append(f'slide {i}: required text missing: {required}')
                if expected.get('disclosure') and norm(expected['disclosure']) not in joined:
                    errors.append(f'slide {i}: visible disclosure missing')
                if expected.get('table'):
                    target_rows = [[norm(c) for c in row] for row in expected['table']['rows']]
                    if not any([[norm(c) for c in row] for row in t] == target_rows for t in tables):
                        errors.append(f'slide {i}: native table rows/values differ from plan')
                if expected.get('chart'):
                    target_chart = expected['chart']
                    def matches(chart):
                        if len(chart['series']) != len(target_chart['series']):
                            return False
                        for got, want in zip(chart['series'], target_chart['series']):
                            if got['categories'] != target_chart['categories'] or len(got['values']) != len(want['values']):
                                return False
                            if not all(math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-8) for a, b in zip(got['values'], want['values'])):
                                return False
                        return True
                    if not any(matches(c) for c in charts):
                        errors.append(f'slide {i}: native chart categories/values differ from plan')
            summary.append({'slide': i, 'native_text_objects': native_text, 'native_tables': len(tables),
                            'native_charts': len(charts), 'pictures': len(root.findall('.//p:pic', NS)),
                            'chart_workbooks': sum(c['embedded_workbook'] for c in charts)})
    return {'passed': not errors, 'errors': errors, 'warnings': warnings, 'slides': summary,
            'limits': 'Checks package/native objects and declared content; text fit, visual composition and application behavior require rendered/manual inspection.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pptx'); ap.add_argument('--plan'); ap.add_argument('--out'); a = ap.parse_args()
    try:
        result = check(a.pptx, json.loads(Path(a.plan).read_text(encoding='utf-8')) if a.plan else None)
    except (OSError, ValueError, KeyError, AttributeError, TypeError, zipfile.BadZipFile, ET.ParseError) as e:
        result = {'passed': False, 'errors': [str(e)], 'warnings': [], 'slides': []}
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        out = Path(a.out)
        if out.resolve() in [Path(p).resolve() for p in (a.pptx, a.plan) if p]:
            ap.error('Report cannot overwrite an input')
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(data + '\n', encoding='utf-8')
    print(data); return 0 if result['passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
