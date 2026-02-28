from pathlib import Path

runbook = Path('docs/OPERATIONS_RUNBOOK.md')
assert runbook.exists(), 'runbook missing'
text = runbook.read_text(encoding='utf-8')
for needle in [
    'Deployment runbook',
    'Rollback runbook',
    'Backup and restore runbook',
    'Audit operations runbook',
    'Metrics and telemetry runbook',
    'Migration runbook',
    'Sandbox / ACL runbook',
    'release_check.sh',
    'rollback_check.sh',
    'restore_drill.sh',
]:
    assert needle in text, f'missing runbook section: {needle}'

for relpath in ['README.md', 'DEPLOYMENT.md']:
    t = Path(relpath).read_text(encoding='utf-8')
    assert 'OPERATIONS_RUNBOOK.md' in t, f'missing link in {relpath}'

print('OK_V39_RUNBOOK_SMOKE')
