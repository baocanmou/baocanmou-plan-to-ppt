#!/usr/bin/env python3
"""Extract explicitly supplied local sources. No API calls or recursive scan."""
import argparse
import csv
import hashlib
import io
import json
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
MAX_BYTES = 80 * 1024 * 1024


def sha(value):
    return hashlib.sha256(value).hexdigest()


def safe_xml(z, name):
    if z.getinfo(name).file_size > MAX_BYTES:
        raise ValueError('XML part exceeds 80 MiB')
    data = z.read(name)
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity declarations are unsupported')
    return ET.fromstring(data)


def extract(path):
    suffix = path.suffix.lower()
    if suffix in ('.md', '.txt'):
        text = path.read_bytes().decode('utf-8-sig', errors='strict')
        return [{'locator': f'line:{i}', 'text': line, 'kind': 'text'}
                for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    if suffix in ('.csv', '.tsv'):
        text = path.read_bytes().decode('utf-8-sig', errors='strict')
        rows = list(csv.reader(io.StringIO(text), delimiter='\t' if suffix == '.tsv' else ','))
        return [{'locator': f'row:{i}', 'text': ' | '.join(row), 'cells': row, 'kind': 'table-row'}
                for i, row in enumerate(rows, 1) if any(row)]
    if suffix == '.docx':
        with zipfile.ZipFile(path) as z:
            root = safe_xml(z, 'word/document.xml')
        out = []
        body = root.find(W + 'body')
        if body is None:
            raise ValueError('DOCX has no body')
        for i, block in enumerate(body, 1):
            if block.tag == W + 'p':
                text = ''.join(t.text or '' for t in block.iter(W + 't'))
                if text.strip():
                    out.append({'locator': f'block:{i}', 'text': text, 'kind': 'text'})
            elif block.tag == W + 'tbl':
                for j, row in enumerate(block.findall(W + 'tr'), 1):
                    cells = ['\n'.join(''.join(t.text or '' for t in p.iter(W + 't'))
                                       for p in cell.findall(W + 'p')) for cell in row.findall(W + 'tc')]
                    out.append({'locator': f'block:{i}/row:{j}', 'text': ' | '.join(cells),
                                'cells': cells, 'kind': 'table-row'})
        return out
    if suffix == '.pptx':
        with zipfile.ZipFile(path) as z:
            p = safe_xml(z, 'ppt/presentation.xml')
            rel = safe_xml(z, 'ppt/_rels/presentation.xml.rels')
            targets = {r.attrib['Id']: r.attrib['Target'] for r in rel}
            ns = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
            rid = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
            out = []
            for i, item in enumerate(p.findall(f'{ns}sldIdLst/{ns}sldId'), 1):
                target = targets[item.attrib[rid]]
                name = target.lstrip('/') if target.startswith('/') else 'ppt/' + target
                if '..' in Path(name).parts:
                    raise ValueError('Unexpected slide relationship path')
                root = safe_xml(z, name)
                text = '\n'.join(t.text or '' for t in root.iter(A + 't'))
                out.append({'locator': f'slide:{i}', 'text': text, 'kind': 'slide-text'})
            return out
    if suffix == '.pdf':
        try:
            import pymupdf
        except ImportError:
            try:
                from pypdf import PdfReader
                from pypdf.errors import PdfReadError
            except ImportError as e:
                raise ValueError('PDF needs PyMuPDF, pypdf or the host PDF reader; no package was installed') from e
            try:
                pdf = PdfReader(path, strict=True)
                if pdf.is_encrypted:
                    raise ValueError('Encrypted PDF requires an authorized unlocked copy')
                return [{'locator': f'page:{i}', 'text': text, 'kind': 'pdf-text',
                         'needs_visual_read': len(text.strip()) < 25}
                        for i, page in enumerate(pdf.pages, 1) for text in [page.extract_text() or '']]
            except PdfReadError as e:
                raise ValueError(f'Cannot read PDF: {e}') from e
        out = []
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass:
                raise ValueError('Encrypted PDF requires an authorized unlocked copy')
            for i, page in enumerate(pdf, 1):
                text = page.get_text('text')
                out.append({'locator': f'page:{i}', 'text': text, 'kind': 'pdf-text',
                            'needs_visual_read': len(text.strip()) < 25})
        return out
    raise ValueError(f'Unsupported format {suffix}; use the host reader with page/row locators')


def build(paths):
    documents, chunks, failures, seen = [], [], [], set()
    for raw in paths:
        path = Path(raw)
        name = unicodedata.normalize('NFC', path.name)
        try:
            if name in seen:
                raise ValueError('Duplicate filename; rename explicit inputs before extraction')
            seen.add(name)
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise ValueError('Expected a file no larger than 80 MiB')
            digest = sha(path.read_bytes())
            parts = extract(path)
            if not any(p['text'].strip() for p in parts):
                raise ValueError('No extractable text; use OCR/host visual reader')
            if any('\ufffd' in p['text'] for p in parts):
                raise ValueError('Replacement character; verify original encoding')
            doc_id = 'D' + sha(name.encode())[:10]
            documents.append({'id': doc_id, 'name': name, 'sha256': digest, 'format': path.suffix.lower()})
            chunks.extend({'id': doc_id + ':' + part['locator'], 'document_id': doc_id,
                           'sha256': sha(part['text'].encode()), **part} for part in parts)
        except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as e:
            failures.append({'name': name, 'error': str(e)})
    return {'schema_version': '1.0', 'documents': documents, 'chunks': chunks,
            'failures': failures,
            'limits': ['Extraction is not factual verification.',
                       'Image text, charts, tracked revisions and merged-cell semantics need host review.',
                       'Chunk IDs follow name/location; inserted paragraphs may shift IDs.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('files', nargs='+'); ap.add_argument('--out', required=True)
    args = ap.parse_args(); out = Path(args.out)
    if out.resolve() in [Path(f).resolve() for f in args.files]:
        ap.error('Output cannot overwrite a source')
    result = build(args.files)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'documents': len(result['documents']), 'chunks': len(result['chunks']),
                      'failures': result['failures']}, ensure_ascii=False))
    return 2 if result['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
