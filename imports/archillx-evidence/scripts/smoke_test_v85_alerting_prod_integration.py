from pathlib import Path

files = [
    Path("docs/ALERTING_PRODUCTION_INTEGRATION.md"),
    Path("docs/ALERTING.md"),
    Path("deploy/prometheus/docker-compose.alerting.example.yml"),
    Path("deploy/alertmanager/alertmanager.example.yml"),
]
for f in files:
    assert f.exists(), f"missing {f}"

text = Path("docs/ALERTING_PRODUCTION_INTEGRATION.md").read_text()
assert "docker-compose.prod.yml" in text
assert "docker-compose.alerting.example.yml" in text
assert "/v1/metrics" in text
assert "Rollout order" in text
print("OK_V85_ALERTING_PROD_INTEGRATION_SMOKE")
