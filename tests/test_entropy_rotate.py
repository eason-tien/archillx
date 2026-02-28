from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_entropy_rotate_creates_archive_and_index(tmp_path):
    evidence = tmp_path / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    src = evidence / 'entropy_engine.jsonl'
    src.write_text('\n'.join([
        json.dumps({'timestamp': '2026-02-28T00:00:00Z', 'score': 0.2}),
        json.dumps({'timestamp': '2026-02-28T00:10:00Z', 'score': 0.4}),
    ]) + '\n', encoding='utf-8')

    proc = subprocess.run(
        ['python', str(Path(__file__).resolve().parents[1] / 'scripts' / 'entropy' / 'rotate_entropy_evidence.py')],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert 'ROTATED=' in proc.stdout

    archives = sorted((evidence / 'archives').glob('entropy_engine_*.jsonl'))
    assert archives
    idx = json.loads((evidence / 'index.json').read_text(encoding='utf-8'))
    assert isinstance(idx, list) and idx
    assert idx[-1]['lines'] == 2
    assert idx[-1]['sha256']
    assert src.read_text(encoding='utf-8') == ''
