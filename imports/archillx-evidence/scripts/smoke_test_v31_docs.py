from pathlib import Path
import json

md = Path('docs/METRICS_DASHBOARD.md')
assert md.exists(), 'metrics dashboard doc missing'
text = md.read_text()
for phrase in [
    'archillx_governor_decision_blocked_total',
    'archillx_skill_invoke_failure_total',
    'archillx_cron_failure_total',
    'archillx_sandbox_sandbox_execute_failed_total',
    'Grafana example',
    'Telemetry response structure',
    'history.windows.last_60s',
    'History-aware alert suggestions',
]:
    assert phrase in text, f'missing doc phrase: {phrase}'

js = Path('deploy/grafana/archillx-dashboard.json')
assert js.exists(), 'grafana dashboard missing'
obj = json.loads(js.read_text())
assert obj['title'] == 'ArcHillx Overview'
assert len(obj['panels']) >= 4
tele = Path('docs/TELEMETRY_API.md')
assert tele.exists(), 'telemetry api doc missing'
tele_text = tele.read_text()
for phrase in ['snapshot', 'aggregate', 'history', 'last_60s', 'last_300s', 'last_3600s']:
    assert phrase in tele_text, f'missing telemetry phrase: {phrase}'
print('OK_V34_DASHBOARD_DOCS_SMOKE')
