#!/usr/bin/env python3
"""Find direct slide dependencies affected by source changes; does not edit a deck."""
import argparse
import json
from pathlib import Path


def impact(plan, old, new):
    before = {c['id']: c for c in old['chunks']}; after = {c['id']: c for c in new['chunks']}
    changed = {cid for cid, c in before.items() if cid not in after or c['sha256'] != after[cid]['sha256']}
    added = set(after) - set(before)
    ids = {c['id'] for c in plan['claims'] if any(r['chunk_id'] in changed for r in c.get('sources', []))}
    return {'changed_or_removed_chunks': sorted(changed), 'added_chunks': sorted(added),
            'affected_claim_ids': sorted(ids),
            'affected_slides': [{'id': s['id'], 'title': s['title']} for s in plan['slides']
                                if ids.intersection(s.get('claim_ids', []))],
            'review_required': bool(changed or added or new.get('failures')),
            'limits': 'Direct dependencies only. New facts, shifted paragraph IDs and indirect strategy effects need review.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--old-sources', required=True); ap.add_argument('--new-sources', required=True)
    a = ap.parse_args(); read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
    print(json.dumps(impact(read(a.plan), read(a.old_sources), read(a.new_sources)), ensure_ascii=False, indent=2))
