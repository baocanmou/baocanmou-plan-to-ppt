#!/usr/bin/env python3
"""Build deterministic plugin and standalone Skill archives using stdlib only."""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '__pycache__', 'dist', '.work', 'node_modules', '.venv'}


def files(root):
    return [p for p in sorted(root.rglob('*')) if p.is_file()
            and not (set(p.relative_to(root).parts) & EXCLUDED)
            and p.name != '.DS_Store' and p.suffix != '.pyc'
            and not p.name.startswith('.env')]


def archive(source, output, top):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in files(source):
            info = zipfile.ZipInfo(top + '/' + p.relative_to(source).as_posix(),
                                   date_time=(2026, 9, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
    with zipfile.ZipFile(output) as z:
        if z.testzip():
            raise ValueError('Archive CRC validation failed')


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/verify_release.py')], check=True)
    manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    name, version = manifest['name'], manifest['version']
    out = ROOT / 'dist'; out.mkdir(exist_ok=True)
    names = [f'{name}-plugin-v{version}.zip', f'{name}-skill-v{version}.zip']
    archive(ROOT, out / names[0], name)
    archive(ROOT / 'skills' / name, out / names[1], name)
    for suffix in ('pptx', 'pdf'):
        name_out = 'example.' + suffix
        shutil.copy2(ROOT / 'skills' / name / 'examples' / ('山间来信_策划提案示范.' + suffix), out / name_out)
        names.append(name_out)
    lines = [hashlib.sha256((out / n).read_bytes()).hexdigest() + '  ' + n for n in names]
    (out / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
