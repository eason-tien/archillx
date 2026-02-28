#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    rel_dir = ROOT / 'evidence' / 'releases'
    rel_dir.mkdir(parents=True, exist_ok=True)
    sample_release = {
        'timestamp': '2026-02-27T00:00:00Z',
        'mode': 'deploy',
        'passed': False,
        'summary': {'checks_total': 10, 'checks_failed': 2, 'errors_failed': 1},
        'results': [
            {'name': 'migration_state', 'ok': False, 'severity': 'error', 'detail': 'behind'},
            {'name': 'sandbox_image_present', 'ok': False, 'severity': 'error', 'detail': 'missing image'},
        ],
        'evidence': 'evidence/releases/release_check_sample.json',
    }
    sample_rollback = {
        'timestamp': '2026-02-27T01:00:00Z',
        'mode': 'deploy',
        'passed': True,
        'summary': {'checks_total': 8, 'checks_failed': 0, 'errors_failed': 0},
        'results': [],
        'evidence': 'evidence/releases/rollback_check_sample.json',
    }
    (rel_dir / 'release_check_20260227_000000.json').write_text(json.dumps(sample_release), encoding='utf-8')
    (rel_dir / 'rollback_check_20260227_010000.json').write_text(json.dumps(sample_rollback), encoding='utf-8')

    proc = subprocess.run([sys.executable, 'scripts/gate_summary.py', '--limit', '5', '--json'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        return 1
    payload = json.loads(proc.stdout)
    for key in ('json', 'markdown', 'html'):
        if not (ROOT / payload[key]).exists():
            raise SystemExit(f'missing generated artifact: {payload[key]}')
    md = (ROOT / payload['markdown']).read_text(encoding='utf-8')
    assert 'ArcHillx Gate Summary' in md
    assert 'migration_state' in md
    html = (ROOT / payload['html']).read_text(encoding='utf-8')
    assert '<html>' in html.lower()
    print('OK_V41_GATE_SUMMARY_SMOKE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
