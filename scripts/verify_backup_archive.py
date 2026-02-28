#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate an ArcHillx backup archive')
    parser.add_argument('archive', help='Path to archillx_backup_*.tar.gz')
    parser.add_argument('--json', action='store_true', help='Emit JSON summary')
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.exists():
        raise SystemExit(f'archive not found: {archive}')

    with tarfile.open(archive, 'r:gz') as tf:
        names = tf.getnames()

    sql_files = [n for n in names if Path(n).name.startswith('mysql_') and n.endswith('.sql')]
    meta_files = [n for n in names if Path(n).name.startswith('backup_meta_')]
    evidence_entries = [n for n in names if n == 'evidence' or n.startswith('evidence/')]

    payload = {
        'archive': str(archive),
        'ok': bool(sql_files and meta_files),
        'sql_files': sql_files,
        'meta_files': meta_files,
        'has_evidence': bool(evidence_entries),
        'entry_count': len(names),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for k, v in payload.items():
            print(f'{k}={json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, bool)) else v}')
    if not payload['ok']:
        raise SystemExit(2)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
