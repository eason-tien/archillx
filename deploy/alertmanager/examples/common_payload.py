from __future__ import annotations

from typing import Any, Dict, List

OWNER_MAP = {
    "platform": "platform-oncall",
    "governance": "governance-reviewer",
    "security": "security-oncall",
    "release": "release-manager",
    "recovery": "recovery-operator",
}


class PayloadValidationError(ValueError):
    """Raised when the incoming Alertmanager payload is invalid."""


def validate_alert_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise PayloadValidationError("payload must be a JSON object")
    alerts = payload.get("alerts")
    if alerts is None:
        raise PayloadValidationError("payload.alerts is required")
    if not isinstance(alerts, list):
        raise PayloadValidationError("payload.alerts must be a list")
    for i, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            raise PayloadValidationError(f"payload.alerts[{i}] must be an object")


def build_alert_records(payload: Dict[str, Any]) -> Dict[str, Any]:
    validate_alert_payload(payload)

    group_labels = payload.get("groupLabels", {}) or {}
    common_labels = payload.get("commonLabels", {}) or {}
    common_annotations = payload.get("commonAnnotations", {}) or {}
    alerts = payload.get("alerts", []) or []

    alert_domain = common_labels.get("alert_domain") or "unknown"
    receiver = payload.get("receiver")
    severity = common_labels.get("severity") or "unknown"
    owner = OWNER_MAP.get(alert_domain, "unmapped-owner")

    records: List[Dict[str, Any]] = []
    for alert in alerts:
        labels = alert.get("labels", {}) or {}
        annotations = alert.get("annotations", {}) or {}
        records.append(
            {
                "fingerprint": alert.get("fingerprint"),
                "status": alert.get("status") or payload.get("status"),
                "alertname": labels.get("alertname") or group_labels.get("alertname"),
                "alert_domain": labels.get("alert_domain") or alert_domain,
                "severity": labels.get("severity") or severity,
                "summary": annotations.get("summary") or common_annotations.get("summary"),
                "runbook": annotations.get("runbook") or common_annotations.get("runbook"),
                "startsAt": alert.get("startsAt"),
                "generatorURL": alert.get("generatorURL") or payload.get("generatorURL"),
                "externalURL": payload.get("externalURL"),
            }
        )

    return {
        "receiver": receiver,
        "status": payload.get("status"),
        "owner": owner,
        "alert_domain": alert_domain,
        "severity": severity,
        "group_alertname": group_labels.get("alertname"),
        "record_count": len(records),
        "records": records,
    }
