#!/usr/bin/env python3
"""Validate provenance and declared data; never certify semantic truth or design."""
import argparse
import json
import math
import re
import sys
from pathlib import Path


def normalized(s):
    return re.sub(r'\s+', '', str(s))


def numbers(s):
    return set(re.findall(r'[-+]?\d+(?:\.\d+)?%?', str(s)))


def check_binding(binding, value, label, sid, refs, claims, chunks, disclosure, errors):
    if label is not None and normalized(binding.get('label', '')) != normalized(label):
        errors.append(f'{sid}: bound category/row label differs from displayed label')
    cid = binding.get('claim_id')
    claim = claims.get(cid)
    if cid not in refs or claim is None:
        errors.append(f'{sid}: data binding must reference a claim used by this slide'); return
    if normalized(binding.get('value')) != normalized(value):
        errors.append(f'{sid}: bound value differs from displayed data'); return
    if claim.get('kind') == 'proposal':
        if not disclosure:
            errors.append(f'{sid}: proposed data needs a visible disclosure')
        return
    if claim.get('kind') == 'calculation':
        result = claim.get('calculation', {}).get('result')
        try:
            if not math.isclose(float(value), float(result), rel_tol=1e-6, abs_tol=1e-8):
                errors.append(f'{sid}: data differs from declared calculation result')
        except (ValueError, TypeError):
            errors.append(f'{sid}: calculated binding must use the numeric result; format units separately')
        return
    if claim.get('kind') != 'source':
        errors.append(f'{sid}: unknown facts cannot populate a data point'); return
    chunk_id = binding.get('chunk_id'); quote = binding.get('quote', '')
    chunk = chunks.get(chunk_id)
    if chunk_id not in {r.get('chunk_id') for r in claim.get('sources', [])}:
        errors.append(f'{sid}: binding source is outside its claim evidence')
    if not chunk or not quote or normalized(quote) not in normalized(chunk['text']):
        errors.append(f'{sid}: data quote does not occur in its source'); return
    if numbers(value) - numbers(quote):
        errors.append(f'{sid}: displayed data number absent from bound source quote')
    if label and normalized(label) not in normalized(quote):
        errors.append(f'{sid}: category/row label absent from bound quote; use an unambiguous source excerpt')


def check_methodology(plan, claims, errors):
    method = plan.get('methodology')
    if method is None:
        return  # General reports and v1.0 plans remain valid.
    if method.get('id') != 'moushuming' or method.get('mode') not in ('full', 'partial', 'hypothesis'):
        errors.append('methodology: declare moushuming and full/partial/hypothesis mode'); return
    slides = {s.get('id'): s for s in plan.get('slides', [])}

    def claim_refs(ids, where, slide_ids=None):
        if not isinstance(ids, list) or not ids or any(i not in claims for i in ids):
            errors.append(f'methodology {where}: valid claim_ids required'); return
        if slide_ids is not None:
            if not slide_ids or any(s not in slides for s in slide_ids):
                errors.append(f'methodology {where}: valid slide_ids required'); return
            covered = {c for s in slide_ids for c in slides[s].get('claim_ids', [])}
            if not set(ids).issubset(covered):
                errors.append(f'methodology {where}: claims are not covered by the declared slides')

    center = method.get('center', {})
    for field in ('value_claim_ids', 'mission_claim_ids', 'vision_claim_ids'):
        claim_refs(center.get(field), f'center.{field}', center.get('slide_ids', []))
    if method.get('mode') == 'full':
        for field in ('assessment_claim_ids', 'source_card_claim_ids', 'founder_claim_ids'):
            ids = method.get('inputs', {}).get(field, [])
            claim_refs(ids, f'inputs.{field}')
            if any(claims.get(c, {}).get('kind') != 'source' for c in ids):
                errors.append(f'methodology inputs.{field}: full mode needs source-backed inputs')

    groups = {}
    for stage in ('mao', 'shu', 'ming'):
        entries = method.get(stage, [])
        if not entries:
            errors.append(f'methodology: {stage} needs an applied action or an explicit scoped gap')
        groups[stage] = {}
        for item in entries:
            key = item.get('id')
            if not key or key in groups[stage]:
                errors.append(f'methodology {stage}: missing/duplicate action id'); continue
            groups[stage][key] = item
            claim_refs(item.get('claim_ids'), key, item.get('slide_ids', []))
            fields = {'mao': ('category', 'difference', 'proof'),
                      'shu': ('task', 'perception', 'scene'),
                      'ming': ('audience', 'channel', 'content', 'rhythm', 'feedback')}[stage]
            for field in fields:
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f'methodology {key}: missing {field}')
    for key, item in groups['shu'].items():
        if item.get('mao_id') not in groups['mao']:
            errors.append(f'methodology {key}: design needs a valid positioning decision')
    for key, item in groups['ming'].items():
        if item.get('mao_id') not in groups['mao']:
            errors.append(f'methodology {key}: communication needs a valid positioning decision')
        ids = item.get('shu_ids', [])
        if not ids or any(i not in groups['shu'] for i in ids):
            errors.append(f'methodology {key}: communication needs existing design/expression actions')
        elif any(groups['shu'][i].get('mao_id') != item.get('mao_id') for i in ids):
            errors.append(f'methodology {key}: communication and design point to different positioning decisions')


def check(plan, sources):
    errors, warnings = [], []
    chunks = {x['id']: x for x in sources.get('chunks', [])}
    claims = {}
    if sources.get('failures'):
        errors.append('Sources contain extraction failures')
    if plan.get('schema_version') != '1.0':
        errors.append('schema_version must be 1.0')
    project = plan.get('project', {})
    for k in ('title', 'audience', 'purpose'):
        if not isinstance(project.get(k), str) or not project[k].strip():
            errors.append(f'project.{k} is required')
    for c in plan.get('claims', []):
        cid = c.get('id')
        if not cid or cid in claims:
            errors.append(f'Missing/duplicate claim ID: {cid}'); continue
        claims[cid] = c
        kind = c.get('kind')
        if kind not in ('source', 'proposal', 'calculation', 'unknown'):
            errors.append(f'{cid}: unknown claim kind {kind}')
        if not c.get('text'):
            errors.append(f'{cid}: empty claim')
        if kind in ('source', 'calculation') and not c.get('sources'):
            errors.append(f'{cid}: factual/calculated claim needs sources')
        quotes = []
        for ref in c.get('sources', []):
            chunk = chunks.get(ref.get('chunk_id')); quote = ref.get('quote', '')
            if chunk is None:
                errors.append(f'{cid}: unknown source chunk {ref.get("chunk_id")}')
            elif not quote or normalized(quote) not in normalized(chunk['text']):
                errors.append(f'{cid}: quote does not occur in source {ref.get("chunk_id")}')
            else:
                quotes.append(quote)
        if kind == 'source':
            missing = numbers(c.get('text', '')) - numbers(' '.join(quotes))
            if missing:
                errors.append(f'{cid}: numbers absent from evidence: {sorted(missing)}; declare a calculation if transformed')
        if kind == 'calculation':
            calc = c.get('calculation', {}); values = calc.get('values', [])
            if not values or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
                errors.append(f'{cid}: calculation needs finite numbers'); continue
            funcs = {'sum': lambda: sum(values), 'difference': lambda: values[0] - sum(values[1:]),
                     'ratio': lambda: values[0] / values[1]}
            try:
                expected = funcs[calc['operation']]()
                if not math.isclose(expected, float(calc['result']), rel_tol=1e-6, abs_tol=1e-6):
                    errors.append(f'{cid}: calculation result differs from inputs')
            except (KeyError, IndexError, ZeroDivisionError, TypeError, ValueError):
                errors.append(f'{cid}: invalid calculation')
            warnings.append(f'{cid}: verify units and source-to-operand mapping manually')
    slide_ids = set(); slides = plan.get('slides', [])
    if not slides:
        errors.append('No slides')
    if project.get('slide_count') is not None and project['slide_count'] != len(slides):
        errors.append('Slide count differs from project.slide_count')
    for s in slides:
        sid = s.get('id')
        if not sid or sid in slide_ids:
            errors.append(f'Missing/duplicate slide ID: {sid}')
        slide_ids.add(sid)
        for key in ('title', 'purpose', 'layout'):
            if not s.get(key):
                errors.append(f'{sid}: missing {key}')
        refs = s.get('claim_ids', [])
        for cid in refs:
            if cid not in claims:
                errors.append(f'{sid}: unknown claim {cid}')
            elif claims[cid]['kind'] == 'unknown' and not s.get('disclosure'):
                errors.append(f'{sid}: unresolved fact needs a visible disclosure')
        if not refs:
            warnings.append(f'{sid}: no declared claims; review content coverage')
        table = s.get('table')
        if table:
            rows = table.get('rows', [])
            if not rows or not rows[0] or len({len(r) for r in rows}) != 1:
                errors.append(f'{sid}: table must be a nonempty rectangular matrix')
            bindings = {}
            for binding in table.get('bindings', []):
                coordinate = (binding.get('row'), binding.get('column'))
                if coordinate in bindings:
                    errors.append(f'{sid}: duplicate table binding {coordinate}')
                bindings[coordinate] = binding
            for r, row in enumerate(rows[1:], 1):
                for col, value in enumerate(row):
                    if numbers(value):
                        binding = bindings.get((r, col))
                        if not binding:
                            errors.append(f'{sid}: numeric table cell ({r},{col}) needs a binding')
                        else:
                            check_binding(binding, value, row[0], sid, refs, claims, chunks, s.get('disclosure'), errors)
            for r, col in bindings:
                if not isinstance(r, int) or not isinstance(col, int) or r < 1 or r >= len(rows) or col < 0 or col >= len(rows[r]):
                    errors.append(f'{sid}: table binding coordinates are invalid')
            for total in table.get('totals', []):
                try:
                    actual = sum(float(str(rows[r][total['column']]).replace(',', '')) for r in total['rows'])
                    if not math.isclose(actual, float(total['expected']), rel_tol=1e-6):
                        errors.append(f'{sid}: table total mismatch')
                except (ValueError, TypeError, IndexError, KeyError):
                    errors.append(f'{sid}: invalid table total contract')
        chart = s.get('chart')
        if chart:
            if not chart.get('unit'):
                errors.append(f'{sid}: chart needs a unit')
            cats = chart.get('categories', [])
            if not cats or not chart.get('series'):
                errors.append(f'{sid}: chart has no data')
            for series in chart.get('series', []):
                vals = series.get('values', [])
                if len(vals) != len(cats) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vals):
                    errors.append(f'{sid}: chart values are incomplete or nonfinite')
            bindings = {}
            for binding in chart.get('bindings', []):
                coordinate = (binding.get('series'), binding.get('index'))
                if coordinate in bindings:
                    errors.append(f'{sid}: duplicate chart binding {coordinate}')
                bindings[coordinate] = binding
            for j, series in enumerate(chart.get('series', [])):
                for k, value in enumerate(series.get('values', [])):
                    binding = bindings.get((j, k))
                    if not binding:
                        errors.append(f'{sid}: chart point ({j},{k}) needs a binding')
                    elif k < len(cats):
                        check_binding(binding, value, cats[k], sid, refs, claims, chunks, s.get('disclosure'), errors)
            for j, k in bindings:
                if not isinstance(j, int) or not isinstance(k, int) or j < 0 or j >= len(chart.get('series', [])) or k < 0 or k >= len(chart['series'][j].get('values', [])):
                    errors.append(f'{sid}: chart binding coordinates are invalid')
            for total in chart.get('totals', []):
                try:
                    if not math.isclose(sum(chart['series'][total['series']]['values']), float(total['expected']), rel_tol=1e-6):
                        errors.append(f'{sid}: chart total differs from declared sample size')
                except (IndexError, KeyError, ValueError, TypeError):
                    errors.append(f'{sid}: invalid chart total contract')
        if len(normalized(s.get('title', ''))) > 30:
            warnings.append(f'{sid}: long title; inspect wrapping')
    for conflict in plan.get('conflicts', []):
        for cid in conflict.get('claim_ids', []):
            if cid not in claims:
                errors.append(f'Conflict references missing claim {cid}')
        if not conflict.get('resolution'):
            warnings.append(f'Unresolved source conflict: {conflict.get("id", "unnamed")}')
    check_methodology(plan, claims, errors)
    return {'passed': not errors, 'errors': errors, 'warnings': warnings,
            'slides': len(slides), 'claims': len(claims),
            'limits': 'Checks quotations/arithmetic, not factual truth, omitted claims, semantic support or design.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--sources', required=True); ap.add_argument('--out')
    args = ap.parse_args()
    try:
        result = check(json.loads(Path(args.plan).read_text(encoding='utf-8')), json.loads(Path(args.sources).read_text(encoding='utf-8')))
    except (ValueError, OSError, TypeError, KeyError) as e:
        result = {'passed': False, 'errors': [str(e)], 'warnings': []}
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        if out.resolve() in (Path(args.plan).resolve(), Path(args.sources).resolve()):
            ap.error('Report cannot overwrite input')
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(data + '\n', encoding='utf-8')
    print(data)
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
