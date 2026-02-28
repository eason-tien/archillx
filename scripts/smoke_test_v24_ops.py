from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / 'docker-compose.prod.override.example.yml',
    ROOT / 'deploy/nginx/archillx.tls.conf',
    ROOT / 'deploy/logrotate/archillx',
    ROOT / 'scripts/backup_stack.sh',
    ROOT / 'scripts/restore_stack.sh',
    ROOT / 'scripts/archive_audit.sh',
    ROOT / 'deploy/systemd/archillx-backup.service',
    ROOT / 'deploy/systemd/archillx-backup.timer',
    ROOT / 'deploy/systemd/archillx-audit-archive.service',
    ROOT / 'deploy/systemd/archillx-audit-archive.timer',
]
missing = [str(p) for p in required if not p.exists()]
assert not missing, f"missing files: {missing}"
text = (ROOT / '.env.prod.example').read_text()
assert 'BACKUP_DIR=' in text
assert 'BACKUP_KEEP_DAYS=' in text
print('OK_V24_OPS_SMOKE')
