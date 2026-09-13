#!/usr/bin/env python3
"""Local-only Skill installation. Never overwrite without an explicit backup."""
import argparse
import datetime
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'baocanmou-plan-to-ppt'
SOURCE = ROOT / 'skills' / NAME


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def install(destination, replace=False, dry_run=False):
    destination = destination.expanduser().absolute()
    if not (SOURCE / 'SKILL.md').is_file():
        raise ValueError('Run this installer from the complete plugin/repository package.')
    if destination.is_symlink():
        raise ValueError('Destination is a symlink. Update its shared source explicitly.')
    if destination.exists() and not destination.is_dir():
        raise ValueError('Destination is not a directory.')
    if destination.exists() and not replace:
        raise ValueError('Destination exists; use --replace only for an intended upgrade.')
    if destination == SOURCE.resolve() or SOURCE.resolve() in destination.parents:
        raise ValueError('Destination must be outside the source Skill.')
    if destination in SOURCE.resolve().parents:
        raise ValueError('Destination must not contain the source repository.')
    record = {'source': str(SOURCE), 'destination': str(destination),
              'dry_run': dry_run, 'file_count': len(hashes(SOURCE))}
    if dry_run:
        return record
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.' + NAME + '-', dir=destination.parent))
    backup = None
    try:
        shutil.copytree(SOURCE, staging, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if hashes(staging) != hashes(SOURCE):
            raise ValueError('Copied file hashes differ; original destination retained.')
        if destination.exists():
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            # Keep old SKILL.md files outside the host's skills discovery directory.
            backup_root = destination.parent.parent / 'skill-backups'
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / (destination.name + '.backup-' + stamp)
            destination.rename(backup)
        staging.rename(destination)
        record.update({'installed': True, 'backup': str(backup) if backup else None,
                       'hashes_verified': True})
        return record
    except Exception:
        if backup and backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=['codex', 'claude'], default='codex')
    parser.add_argument('--target', type=Path, help='Explicit complete Skill destination')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    parent = '.agents' if args.host == 'codex' else '.claude'
    destination = args.target or Path.home() / parent / 'skills' / NAME
    try:
        print(json.dumps(install(destination, args.replace, args.dry_run),
                         ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
