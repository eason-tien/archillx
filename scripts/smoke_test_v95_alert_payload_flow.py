from pathlib import Path

root = Path(__file__).resolve().parents[1]
doc = (root / "docs/ALERTING_RECEIVERS_AND_OWNERS.md").read_text()
for token in [
    "## Example payload flow",
    "```mermaid",
    "flowchart LR",
    "platform-webhook",
    "governance-webhook",
    "security-webhook",
    "release-webhook",
    "recovery-webhook",
    "Field-level interpretation",
    "Minimal receiver decision map",
    "alert_domain=governance",
    "alert_domain=security",
]:
    assert token in doc, token
print("OK_V95_ALERT_PAYLOAD_FLOW_SMOKE")
