#!/usr/bin/env python3
from __future__ import annotations

import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    backup_dir = ROOT / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    archive = backup_dir / f'archillx_backup_{stamp}.tar.gz'
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / f'mysql_{stamp}.sql').write_text('-- sanitized sample dump\n', encoding='utf-8')
        (tdp / f'backup_meta_{stamp}.txt').write_text('sample=true\n', encoding='utf-8')
        (tdp / 'evidence').mkdir()
        (tdp / 'evidence' / 'README.txt').write_text('Sanitized sample evidence bundle.\n', encoding='utf-8')
        with tarfile.open(archive, 'w:gz') as tf:
            for item in tdp.rglob('*'):
                tf.add(item, arcname=item.relative_to(tdp))
    print(archive)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
