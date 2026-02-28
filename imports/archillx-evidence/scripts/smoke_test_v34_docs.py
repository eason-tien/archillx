from pathlib import Path
import json, subprocess, sys
subprocess.check_call([sys.executable, 'scripts/smoke_test_v31_docs.py'])
md = Path('docs/METRICS_DASHBOARD.md').read_text()
for phrase in [
    '## v36 panel refinement',
    'Request Rate (5m)',
    'Top Skill Invocations (15m)',
    'Sandbox Backend Split (1h)',
    'Practical dashboard reading order',
]:
    assert phrase in md, f'missing v36 dashboard phrase: {phrase}'
tele = Path('docs/TELEMETRY_API.md').read_text()
for phrase in [
    '## Dashboard-focused notes (v36)',
    'Top Skill Invocations (15m)',
    'Top Cron Jobs (1h)',
    'Sandbox Backend Split (1h)',
]:
    assert phrase in tele, f'missing telemetry v36 phrase: {phrase}'
obj = json.loads(Path('deploy/grafana/archillx-dashboard.json').read_text())
assert obj['version'] >= 2
assert len(obj['panels']) >= 15
for title in [
    'Request Rate (5m)',
    'HTTP 5xx Rate (5m)',
    'Top Skill Invocations (15m)',
    'Top Cron Jobs (1h)',
    'Sandbox Backend Split (1h)',
]:
    assert any(p.get('title') == title for p in obj['panels']), f'missing panel {title}'
print('OK_V34_DOCS_SMOKE')
