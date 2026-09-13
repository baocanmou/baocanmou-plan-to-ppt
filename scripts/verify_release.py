#!/usr/bin/env python3
"""Offline, standard-library checks for the public distribution and example."""
import importlib.util
import json
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
NAME = 'baocanmou-plan-to-ppt'
SKILL = ROOT / 'skills' / NAME
EXCLUDED = {'.git', '__pycache__', 'dist', '.work', 'node_modules', '.venv'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def module(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / 'scripts' / (name + '.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def main():
    manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    require(manifest['name'] == NAME, 'Manifest name mismatch')
    version = manifest['version']
    require(re.search(r'^  version: ' + re.escape(version) + r'$',
                      (SKILL / 'SKILL.md').read_text(), re.M), 'Skill version mismatch')
    required = ['README.md', 'README.en.md', 'LICENSE', 'NOTICE.md', 'PRIVACY.md',
                'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', 'CITATION.cff',
                'docs/INSTALL.md', 'docs/ATTRIBUTION.md', 'docs/VALIDATION.md',
                'docs/RELEASE_NOTES.md', 'assets/README.md',
                'assets/source/generation-prompts.md',
                '.github/workflows/validate.yml']
    required += [f'skills/{NAME}/{p}' for p in ['SKILL.md', 'NOTICE.md',
        'references/workflow.en.md', 'references/moushuming.en.md',
        'references/licenses/SourceHanSans-OFL.txt']]
    for name in required:
        require((ROOT / name).is_file(), 'Missing required file: ' + name)
    ui = manifest['interface']
    for name in [ui['composerIcon'], ui['logo'], ui['logoDark'], *ui['screenshots']]:
        p = (ROOT / name).resolve()
        require(p.is_relative_to(ROOT) and p.is_file(), 'Missing or unsafe UI asset: ' + name)
        data = p.read_bytes()
        require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG: ' + name)
        width, height = struct.unpack('>II', data[16:24])
        require(width >= 256 and height >= 256, 'UI image too small: ' + name)
    files = [p for p in ROOT.rglob('*') if p.is_file()
             and not set(p.relative_to(ROOT).parts) & EXCLUDED
             and p.suffix != '.pyc' and p.name != '.DS_Store']
    private = re.compile(r'/(?:Users|Volumes)/|(?:gh[pousr]_[A-Za-z0-9]{20,})|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----')
    link_count = 0
    for p in files:
        require(not p.is_symlink(), 'Public package contains a symlink: ' + str(p.relative_to(ROOT)))
        require(not p.name.startswith('.env'), 'Environment file in release')
        if p.suffix in {'.md', '.json', '.yaml', '.yml', '.cff', '.svg', '.txt'}:
            content = p.read_text(encoding='utf-8')
            require(not private.search(content), 'Private data pattern in ' + str(p.relative_to(ROOT)))
            if p.suffix == '.md':
                require(not any(word in content for word in ['门' + '头', '招' + '牌']),
                        'Unapproved public brand wording in ' + str(p.relative_to(ROOT)))
                for link in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', content):
                    link = link.strip('<>')
                    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', link) or link.startswith('#'):
                        continue
                    target = (p.parent / unquote(link.split('#')[0])).resolve()
                    require(target.is_relative_to(ROOT) and target.exists(),
                            'Broken local link: ' + str(p.relative_to(ROOT)) + ' -> ' + link)
                    link_count += 1
    plan = json.loads((SKILL / 'examples/plan.json').read_text(encoding='utf-8'))
    intake, plancheck, pptxcheck = [module(name) for name in ('intake', 'plancheck', 'pptxcheck')]
    sources = intake.build(sorted((SKILL / 'examples/source').iterdir()))
    require(not sources['failures'], 'Sample extraction failure')
    require(len(sources['chunks']) == 27 and len(plan['claims']) == 20, 'Unexpected sample size')
    result = plancheck.check(plan, sources)
    require(result['passed'], 'Sample plan failed: ' + str(result['errors']))
    pptx = SKILL / 'examples/山间来信_策划提案示范.pptx'
    with zipfile.ZipFile(pptx) as z:
        require(z.testzip() is None, 'PPTX CRC failed')
        for name in z.namelist():
            if name.endswith(('.xml', '.rels')):
                require(not private.search(z.read(name).decode('utf-8')), 'Private data in PPTX: ' + name)
    result = pptxcheck.check(pptx, plan)
    require(result['passed'], 'Actual PPTX failed: ' + str(result['errors']))
    require(len(result['slides']) == 12, 'Wrong slide count')
    pdf = SKILL / 'examples/山间来信_策划提案示范.pdf'
    require(pdf.read_bytes().startswith(b'%PDF-'), 'Missing PDF example')
    for directory in [SKILL / 'tests', ROOT / 'scripts']:
        subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s',
                        str(directory), '-p', 'test_*.py', '-v'], check=True, cwd=ROOT)
    print(json.dumps({'passed': True, 'version': version, 'public_files': len(files),
                      'local_links': link_count, 'source_chunks': len(sources['chunks']),
                      'slides': len(result['slides']),
                      'native_totals': {k: sum(s[k] for s in result['slides']) for k in
                       ['native_text_objects', 'native_tables', 'native_charts', 'pictures', 'chart_workbooks']},
                      'limits': 'No semantic fact-checking or automated visual acceptance.'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
