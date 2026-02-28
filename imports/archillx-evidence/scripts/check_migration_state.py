#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def load_env(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


ROOT = Path(__file__).resolve().parents[1]

def parse_head() -> str | None:
    versions = ROOT / 'alembic' / 'versions'
    if not versions.exists():
        return None
    heads = []
    for f in versions.glob('*.py'):
        txt = f.read_text(encoding='utf-8', errors='ignore')
        m = re.search(r'^revision\s*=\s*[\'"]([^\'"]+)[\'"]', txt, re.M)
        if m:
            heads.append(m.group(1))
    return sorted(heads)[-1] if heads else None


def main() -> int:
    env_file = sys.argv[1] if len(sys.argv) > 1 else '.env.prod'
    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = ROOT / env_path
    load_env(str(env_path))
    require = os.getenv('REQUIRE_MIGRATION_HEAD', 'true').lower() not in ('0','false','no')
    head = parse_head()
    alembic_cmd = shutil.which('alembic')
    if not alembic_cmd:
        print('[ERR] unable to inspect alembic current: alembic CLI not installed')
        return 1 if require else 0
    try:
        out = subprocess.check_output([alembic_cmd, 'current'], text=True, stderr=subprocess.STDOUT, cwd=str(ROOT)).strip()
    except Exception as e:
        print(f'[ERR] unable to inspect alembic current: {e}')
        return 1 if require else 0
    current = out.split()[0] if out else ''
    if head and current == head:
        print(f'[OK] alembic current matches head: {current}')
        return 0
    msg = f'[ERR] alembic current/head mismatch current={current or "<none>"} head={head or "<none>"}'
    print(msg)
    return 1 if require else 0


if __name__ == '__main__':
    raise SystemExit(main())
