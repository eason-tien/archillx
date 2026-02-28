from pathlib import Path

root = Path(__file__).resolve().parents[1]
alert = (root / "deploy/alertmanager/alertmanager.example.yml").read_text()
doc = (root / "docs/ALERTING_RECEIVERS_AND_OWNERS.md").read_text()
for token in ["governance-webhook", "security-webhook", "release-webhook", "recovery-webhook", 'alert_domain="governance"', 'alert_domain="security"']:
    assert token in alert, token
for token in ["| `governance` |", "| `security` |", "| `release` |", "| `recovery` |", "Primary owner", "Primary runbook"]:
    assert token in doc, token
print("OK_V89_ALERT_RECEIVERS_SMOKE")
