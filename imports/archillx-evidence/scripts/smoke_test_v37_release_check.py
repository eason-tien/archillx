#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    local_env = ROOT / '.env.v37.smoke'
    local_env.write_text(
        "\n".join(
            [
                'API_KEY=test',
                'ADMIN_TOKEN=admin',
                'DB_PASSWORD=dbpass',
                'MYSQL_ROOT_PASSWORD=rootpass',
                'ARCHILLX_ENABLE_CODE_EXEC=false',
            ]
        ),
        encoding='utf-8',
    )
    try:
        cmd = [
            'python3', 'scripts/release_check.py',
            '--mode', 'deploy',
            '--env-file', '.env.v37.smoke',
            '--skip-pytest', '--skip-compile', '--skip-preflight', '--skip-compose', '--json'
        ]
        proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        assert proc.returncode == 0, proc.stdout
        data = json.loads(proc.stdout)
        assert data['passed'] is True, data
        assert data['summary']['checks_total'] >= 3, data
        evidence = ROOT / data['evidence']
        assert evidence.exists(), data
    finally:
        if local_env.exists():
            local_env.unlink()
    print('OK_V37_RELEASE_CHECK_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
