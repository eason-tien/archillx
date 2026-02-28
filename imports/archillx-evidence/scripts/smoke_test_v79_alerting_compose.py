from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
required = [
    root / 'deploy/prometheus/prometheus.yml',
    root / 'deploy/prometheus/alert_rules.yml',
    root / 'deploy/prometheus/docker-compose.alerting.example.yml',
    root / 'deploy/alertmanager/alertmanager.example.yml',
    root / 'docs/ALERTING.md',
]
for path in required:
    assert path.exists(), f"missing {path}"
compose = yaml.safe_load((root / 'deploy/prometheus/docker-compose.alerting.example.yml').read_text(encoding='utf-8'))
assert 'services' in compose and 'prometheus' in compose['services'] and 'alertmanager' in compose['services']
print('OK_V79_ALERTING_COMPOSE_SMOKE')
