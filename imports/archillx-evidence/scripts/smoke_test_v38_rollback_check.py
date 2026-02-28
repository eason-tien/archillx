#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_backup(backup_dir: Path) -> Path:
    stamp = '20260227_000000'
    archive = backup_dir / f'archillx_backup_{stamp}.tar.gz'
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / f'mysql_{stamp}.sql').write_text('-- sql dump\n', encoding='utf-8')
        (tdp / f'backup_meta_{stamp}.txt').write_text('meta\n', encoding='utf-8')
        (tdp / 'evidence').mkdir()
        (tdp / 'evidence' / 'dummy.txt').write_text('ok\n', encoding='utf-8')
        with tarfile.open(archive, 'w:gz') as tf:
            for item in tdp.rglob('*'):
                tf.add(item, arcname=item.relative_to(tdp))
    return archive


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        backup_dir = tdp / 'backups'
        backup_dir.mkdir()
        archive = make_backup(backup_dir)
        env_file = tdp / '.env.rollback'
        env_file.write_text(
            '\n'.join([
                'API_KEY=test-api',
                'ADMIN_TOKEN=test-admin',
                'DB_PASSWORD=test-db',
                'MYSQL_ROOT_PASSWORD=test-root',
                f'BACKUP_DIR={backup_dir}',
            ]) + '\n',
            encoding='utf-8',
        )
        cmd = [
            'python3', 'scripts/rollback_check.py',
            '--mode', 'deploy',
            '--env-file', str(env_file),
            '--backup-archive', str(archive),
            '--skip-pytest', '--skip-compile', '--skip-shellcheck', '--skip-migration-check', '--skip-migration-history',
            '--json',
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if proc.returncode != 0:
            raise SystemExit(proc.stdout)
        payload = json.loads(proc.stdout)
        assert payload['passed'] is True, payload
        ev = ROOT / payload['evidence']
        assert ev.exists(), payload['evidence']
        print('OK_V38_ROLLBACK_CHECK_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
