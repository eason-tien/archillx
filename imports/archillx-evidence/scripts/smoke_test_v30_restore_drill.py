#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / 'scripts/verify_backup_archive.py',
    ROOT / 'scripts/restore_drill.sh',
    ROOT / 'deploy/systemd/archillx-restore-drill.service',
    ROOT / 'deploy/systemd/archillx-restore-drill.timer',
]
missing = [str(p) for p in required if not p.exists()]
assert not missing, f'missing files: {missing}'

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    src = td / 'src'
    src.mkdir()
    (src / 'mysql_20260101_000000.sql').write_text('create table t(id int);', encoding='utf-8')
    (src / 'backup_meta_20260101_000000.txt').write_text('timestamp=20260101', encoding='utf-8')
    ev = src / 'evidence'
    ev.mkdir()
    (ev / 'security_audit.jsonl').write_text('{"ok": true}\n', encoding='utf-8')
    arch = td / 'archillx_backup_test.tar.gz'
    with tarfile.open(arch, 'w:gz') as tf:
        for item in src.rglob('*'):
            tf.add(item, arcname=item.relative_to(src))

    out = subprocess.check_output(['python3', str(ROOT / 'scripts/verify_backup_archive.py'), str(arch), '--json'], text=True)
    payload = json.loads(out)
    assert payload['ok'] is True
    env = dict(os.environ)
    env['DRILL_REPORT_DIR'] = str(td / 'reports')
    drill = subprocess.check_output(['bash', str(ROOT / 'scripts/restore_drill.sh'), str(arch)], text=True, env=env)
    assert 'OK_RESTORE_DRILL_REPORT=' in drill

print('OK_V30_RESTORE_DRILL_SMOKE')
